from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime
from typing import Any, AsyncIterator

import feedparser
import httpx

from shared.models.news import RawNewsItem
from ingestion.utils.dedup import hash_url, normalize_url

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class RSSSource:
    name = "rss"

    def __init__(self, feed_urls: list[str], timeout: int = 25) -> None:
        self._feed_urls = feed_urls
        self._timeout = timeout

    async def fetch(self) -> AsyncIterator[RawNewsItem]:
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            timeout=self._timeout,
            follow_redirects=True,
        ) as client:
            for feed_url in self._feed_urls:
                async for item in self._fetch_feed(client, feed_url):
                    yield item

    async def _fetch_feed(
        self, client: httpx.AsyncClient, feed_url: str
    ) -> AsyncIterator[RawNewsItem]:
        logger.info("rss.fetch url=%s", feed_url)
        try:
            response = await client.get(feed_url)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("rss.fetch.error url=%s error=%s", feed_url, exc)
            return

        parsed = feedparser.parse(response.content)
        feed_title = parsed.feed.get("title") or feed_url

        for entry in parsed.entries:
            raw_url = entry.get("link")
            if not raw_url:
                continue

            canonical = normalize_url(raw_url)
            yield RawNewsItem(
                url=raw_url,
                canonical_url=canonical,
                url_hash=hash_url(canonical),
                title=entry.get("title"),
                source=feed_title,
                published_at=_parse_struct_time(entry.get("published_parsed")),
                raw_payload={
                    "feed_url": feed_url,
                    "feed_title": feed_title,
                    "entry": {
                        "title": entry.get("title"),
                        "link": raw_url,
                        "summary": entry.get("summary"),
                        "author": entry.get("author"),
                        "tags": [t.get("term") for t in entry.get("tags", [])],
                        "published": entry.get("published"),
                        "guid": entry.get("id") or entry.get("guid"),
                    },
                },
            )


def _parse_struct_time(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
