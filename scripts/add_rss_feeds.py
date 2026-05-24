from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


# Add feeds here for the simplest workflow:
#
# RSS_FEEDS = [
#     "https://finance.yahoo.com/news/rssindex",
#     {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
# ]
RSS_FEEDS: list[str | dict[str, str]] = [
    "https://www.investing.com/rss/stock.rss",
    "https://www.investing.com/rss/stock_Fundamental.rss",
    "https://seekingalpha.com/feed/investing-strategy",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.nasdaq.com/feed/rssoutbound?category=Stocks",
    "https://scr.zacks.com/rss/pressrelease.aspx",
    "https://investorplace.com/content-feed/",
]


def normalize_feed_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"Invalid RSS feed URL: {url}")

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def feed_name_from_url(url: str) -> str:
    parts = urlsplit(url)
    return parts.netloc.removeprefix("www.")


def coerce_feed(feed: str | dict[str, str]) -> dict[str, str]:
    if isinstance(feed, str):
        url = normalize_feed_url(feed)
        name = feed_name_from_url(url)
        return {"name": name, "url": url, "source_name": name}

    url = normalize_feed_url(feed["url"])
    name = feed.get("name") or feed_name_from_url(url)
    return {
        "name": name,
        "url": url,
        "source_name": feed.get("source_name") or name,
    }


def load_feeds_from_file(path: Path) -> list[str | dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as file:
            return [
                {
                    "name": row.get("name") or "",
                    "url": row["url"],
                    "source_name": row.get("source_name") or "",
                }
                for row in csv.DictReader(file)
                if row.get("url")
            ]

    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def upsert_feeds(conn: psycopg.Connection, feeds: list[dict[str, str]]) -> dict[str, int]:
    stats = {"seen": 0, "inserted": 0, "updated": 0}

    for feed in feeds:
        stats["seen"] += 1
        row = conn.execute(
            """
            INSERT INTO rss_feeds (name, url, source_name, enabled)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (url) DO UPDATE
            SET name = EXCLUDED.name,
                source_name = EXCLUDED.source_name,
                enabled = TRUE,
                updated_at = now()
            RETURNING (xmax = 0) AS inserted
            """,
            (feed["name"], feed["url"], feed["source_name"]),
        ).fetchone()

        if row["inserted"]:
            stats["inserted"] += 1
        else:
            stats["updated"] += 1

    return stats


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Insert RSS feeds into Postgres.")
    parser.add_argument(
        "--file",
        type=Path,
        help=(
            "Optional feed file. Use .txt with one URL per line, or .csv with "
            "url,name,source_name columns."
        ),
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    raw_feeds = load_feeds_from_file(args.file) if args.file else RSS_FEEDS
    feeds_by_url = {}
    for feed in raw_feeds:
        coerced = coerce_feed(feed)
        feeds_by_url[coerced["url"]] = coerced
    feeds = list(feeds_by_url.values())

    if not feeds:
        print("No RSS feeds provided. Add entries to RSS_FEEDS or pass --file.")
        return

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            stats = upsert_feeds(conn, feeds)

    skipped_duplicates = len(raw_feeds) - len(feeds)
    print(f"RSS feeds synced: {stats}, skipped_input_duplicates={skipped_duplicates}")


if __name__ == "__main__":
    main()
