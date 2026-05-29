from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import httpx

from shared.models.news import RawNewsItem
from ingestion.utils.dedup import hash_url, normalize_url

logger = logging.getLogger(__name__)

_BASE_URL = "https://finnhub.io/api/v1/company-news"


class FinnhubSource:
    name = "finnhub"

    def __init__(
        self,
        api_key: str,
        symbols: list[str],
        lookback_days: int = 7,
        timeout: int = 25,
    ) -> None:
        self._headers = {"X-Finnhub-Token": api_key}
        self._symbols = symbols
        self._lookback_days = lookback_days
        self._timeout = timeout

    async def fetch(self) -> AsyncIterator[RawNewsItem]:
        today = datetime.now(timezone.utc).date()
        from_date = (today - timedelta(days=self._lookback_days)).isoformat()
        to_date = today.isoformat()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for symbol in self._symbols:
                async for item in self._fetch_symbol(client, symbol, from_date, to_date):
                    yield item

    async def _fetch_symbol(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> AsyncIterator[RawNewsItem]:
        logger.info("finnhub.fetch symbol=%s from=%s to=%s", symbol, from_date, to_date)
        try:
            response = await client.get(
                _BASE_URL,
                headers=self._headers,
                params={"symbol": symbol, "from": from_date, "to": to_date},
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("finnhub.fetch.error symbol=%s error=%s", symbol, exc)
            return

        for article in response.json():
            url = article.get("url", "")
            if not url:
                continue

            canonical = normalize_url(url)
            yield RawNewsItem(
                url=url,
                canonical_url=canonical,
                url_hash=hash_url(canonical),
                title=article.get("headline"),
                source="finnhub",
                published_at=datetime.fromtimestamp(article["datetime"], tz=timezone.utc)
                if article.get("datetime")
                else None,
                raw_payload=article,
            )
