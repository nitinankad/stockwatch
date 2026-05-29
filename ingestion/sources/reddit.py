from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from shared.models.news import RawNewsItem
from ingestion.utils.dedup import hash_url, normalize_url

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "stockwatch/1.0"}


class RedditSource:
    name = "reddit"

    def __init__(self, subreddits: list[str], timeout: int = 25) -> None:
        self._subreddits = subreddits
        self._timeout = timeout

    async def fetch(self) -> AsyncIterator[RawNewsItem]:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=self._timeout) as client:
            for subreddit in self._subreddits:
                async for item in self._fetch_subreddit(client, subreddit):
                    yield item

    async def _fetch_subreddit(
        self, client: httpx.AsyncClient, subreddit: str
    ) -> AsyncIterator[RawNewsItem]:
        logger.info("reddit.fetch subreddit=%s", subreddit)
        url = f"https://www.reddit.com/r/{subreddit}/new.json"
        try:
            response = await client.get(url, params={"limit": 100})
            response.raise_for_status()
        except Exception as exc:
            logger.warning("reddit.fetch.error subreddit=%s error=%s", subreddit, exc)
            return

        for post in response.json().get("data", {}).get("children", []):
            data = post.get("data", {})
            post_url = data.get("url", "")
            if not post_url or "reddit.com" in post_url:
                continue

            canonical = normalize_url(post_url)
            yield RawNewsItem(
                url=post_url,
                canonical_url=canonical,
                url_hash=hash_url(canonical),
                title=data.get("title"),
                source=f"reddit/r/{subreddit}",
                published_at=datetime.fromtimestamp(data["created_utc"], tz=timezone.utc)
                if data.get("created_utc")
                else None,
                raw_payload={
                    "subreddit": subreddit,
                    "post_id": data.get("id"),
                    "title": data.get("title"),
                    "url": post_url,
                    "score": data.get("score"),
                    "num_comments": data.get("num_comments"),
                    "author": data.get("author"),
                },
            )
