from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncIterator

import httpx

from shared.models.news import RawNewsItem
from ingestion.utils.dedup import hash_url, normalize_url

logger = logging.getLogger(__name__)

_BASE_URL = "https://data.alpaca.markets/v1beta1/news"


class AlpacaNewsSource:
    name = "alpaca"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        symbols: list[str] | None = None,
        timeout: int = 25,
    ) -> None:
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        self._symbols = symbols
        self._timeout = timeout

    async def fetch(self) -> AsyncIterator[RawNewsItem]:
        params: dict = {"limit": 50, "sort": "desc"}
        if self._symbols:
            params["symbols"] = ",".join(self._symbols)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            logger.info("alpaca_news.fetch symbols=%s", self._symbols)
            try:
                response = await client.get(_BASE_URL, headers=self._headers, params=params)
                response.raise_for_status()
            except Exception as exc:
                logger.warning("alpaca_news.fetch.error error=%s", exc)
                return

            for article in response.json().get("news", []):
                raw_url = article.get("url", "")
                if not raw_url:
                    continue

                canonical = normalize_url(raw_url)
                yield RawNewsItem(
                    url=raw_url,
                    canonical_url=canonical,
                    url_hash=hash_url(canonical),
                    title=article.get("headline"),
                    source="alpaca",
                    published_at=_parse_iso(article.get("created_at")),
                    raw_payload=article,
                )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
