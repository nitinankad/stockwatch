from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

import feedparser
import psycopg
import requests
from dotenv import load_dotenv
from newspaper import Article, Config
from openai import OpenAI
from psycopg.rows import dict_row


logger = logging.getLogger("stockwatch.ingestion")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}

SYSTEM_PROMPT = """
You are a financial news analysis engine.

Analyze the provided article and return ONLY valid JSON.

Extract:
- mentioned stock tickers
- company names
- sectors
- event type
- market sentiment
- market significance
- macroeconomic themes
- affected industries
- potential winners
- potential losers
- concise summary

Rules:
- Return valid JSON only
- Do not include markdown
- Do not include explanations
- Use null when uncertain
- market_significance should be 0-1
- sentiment should be: positive / negative / neutral / mixed
- Use the provided schema for the JSON format

Schema:
{
  "tickers": string[],
  "companies": string[],
  "sectors": string[],
  "event_type": string,
  "market_sentiment": positive | negative | neutral | mixed,
  "market_significance": 0 to 1,
  "macroeconomic_themes": string[],
  "affected_industries": string[],
  "potential_winners": string[],
  "potential_losers": string[],
  "summary": string
}
""".strip()


@dataclass(frozen=True)
class Settings:
    database_url: str
    deepseek_api_key: str | None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    proxy_url: str | None = None
    request_timeout_seconds: int = 25
    analyze_articles: bool = True
    retry_failed_articles: bool = False
    playwright_fallback_enabled: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required")

        return cls(
            database_url=database_url,
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY"),
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            proxy_url=os.environ.get("HTTP_PROXY_URL") or os.environ.get("PROXY_URL"),
            request_timeout_seconds=int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "25")),
            analyze_articles=os.environ.get("ANALYZE_ARTICLES", "true").lower()
            in {"1", "true", "yes"},
            retry_failed_articles=os.environ.get("RETRY_FAILED_ARTICLES", "false").lower()
            in {"1", "true", "yes"},
            playwright_fallback_enabled=os.environ.get(
                "PLAYWRIGHT_FALLBACK_ENABLED", "true"
            ).lower()
            in {"1", "true", "yes"},
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def fetch_url(url: str, proxy: str | None = None, timeout: int = 30) -> requests.Response:
    logger.info("fetch.requests.start url=%s proxy=%s", url, bool(proxy))
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "DNT": "1",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
    logger.info("fetch.requests.response url=%s status=%s", url, response.status_code)
    response.raise_for_status()
    return response


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    query = urlencode(
        [
            (key, value)
            for key, value in sorted(parse_qsl(parts.query, keep_blank_values=True))
            if key.lower() not in TRACKING_QUERY_PARAMS
        ],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def parsed_time_to_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(mktime(value), tz=timezone.utc)


def configure_newspaper(settings: Settings) -> Config:
    config = Config()
    config.browser_user_agent = USER_AGENT
    config.request_timeout = settings.request_timeout_seconds
    if settings.proxy_url:
        config.proxies = {
            "http": settings.proxy_url,
            "https": settings.proxy_url,
        }
    return config


def playwright_proxy_config(proxy_url: str | None) -> dict[str, str] | None:
    if not proxy_url:
        return None

    parts = urlsplit(proxy_url)
    server = urlunsplit((parts.scheme, parts.hostname or "", "", "", ""))
    if parts.port:
        server = f"{server}:{parts.port}"

    proxy: dict[str, str] = {"server": server}
    if parts.username:
        proxy["username"] = unquote(parts.username)
    if parts.password:
        proxy["password"] = unquote(parts.password)
    return proxy


def fetch_url_with_playwright(url: str, settings: Settings) -> str:
    logger.info(
        "fetch.playwright.start url=%s proxy=%s",
        url,
        bool(settings.proxy_url),
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright fallback requires `pip install playwright` and "
            "`python -m playwright install chromium`"
        ) from exc

    proxy = playwright_proxy_config(settings.proxy_url)
    timeout_ms = settings.request_timeout_seconds * 1000

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            proxy=proxy,
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            viewport={"width": 1365, "height": 768},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = context.new_page()
        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            logger.info(
                "fetch.playwright.response url=%s status=%s",
                url,
                response.status if response else "none",
            )
            if response and response.status >= 400:
                raise RuntimeError(f"Playwright received HTTP {response.status}")
            page.wait_for_timeout(1500)
            html = page.content()
            logger.info("fetch.playwright.html url=%s chars=%s", url, len(html))
            return html
        finally:
            context.close()
            browser.close()


def parse_article_html(url: str, html: str, settings: Settings) -> dict[str, Any]:
    article = Article(url, config=configure_newspaper(settings))
    article.set_html(html)
    article.parse()
    return {
        "title": article.title or None,
        "text": article.text or None,
        "html": html,
        "top_image_url": article.top_image or None,
        "authors": article.authors or [],
        "publish_date": article.publish_date,
        "meta": {
            "meta_description": article.meta_description,
            "meta_keywords": article.meta_keywords,
            "movies": article.movies,
        },
    }


def extract_article(url: str, settings: Settings) -> dict[str, Any]:
    logger.info("article.extract.requests.start url=%s", url)
    response = fetch_url(
        url,
        proxy=settings.proxy_url,
        timeout=settings.request_timeout_seconds,
    )
    parsed = parse_article_html(url, response.text, settings)
    parsed["meta"]["text_source"] = "requests"
    logger.info(
        "article.extract.requests.done url=%s text_chars=%s title=%s",
        url,
        len(parsed["text"] or ""),
        parsed["title"],
    )
    return parsed


def extract_article_with_playwright(url: str, settings: Settings) -> dict[str, Any]:
    logger.info("article.extract.playwright.start url=%s", url)
    html = fetch_url_with_playwright(url, settings)
    parsed = parse_article_html(url, html, settings)
    parsed["meta"]["text_source"] = "playwright"
    logger.info(
        "article.extract.playwright.done url=%s text_chars=%s title=%s",
        url,
        len(parsed["text"] or ""),
        parsed["title"],
    )
    return parsed


def analyze_article_text(text: str, settings: Settings) -> dict[str, Any]:
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required when ANALYZE_ARTICLES=true")

    logger.info(
        "analysis.start provider=deepseek model=%s text_chars=%s",
        settings.deepseek_model,
        len(text),
    )
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    response = client.chat.completions.create(
        model=settings.deepseek_model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"ARTICLE:\n{text}"},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("AI provider returned an empty response")
    parsed = json.loads(content)
    logger.info(
        "analysis.done provider=deepseek model=%s tickers=%s sentiment=%s significance=%s",
        settings.deepseek_model,
        parsed.get("tickers"),
        parsed.get("market_sentiment"),
        parsed.get("market_significance"),
    )
    return parsed


def ensure_feed(conn: psycopg.Connection, name: str, url: str, source_name: str | None) -> int:
    logger.info("db.feed.ensure name=%s url=%s", name, url)
    row = conn.execute(
        """
        INSERT INTO rss_feeds (name, url, source_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (url) DO UPDATE
        SET name = EXCLUDED.name,
            source_name = COALESCE(EXCLUDED.source_name, rss_feeds.source_name),
            enabled = TRUE,
            updated_at = now()
        RETURNING id
        """,
        (name, url, source_name),
    ).fetchone()
    return row["id"]


def upsert_rss_article(
    conn: psycopg.Connection,
    feed_id: int,
    source_name: str | None,
    entry: Any,
) -> tuple[int, bool, str]:
    raw_url = entry.get("link")
    if not raw_url:
        raise ValueError("RSS entry does not include a link")

    canonical_url = normalize_url(raw_url)
    url_hash = hash_url(canonical_url)
    published_at = parsed_time_to_datetime(entry.get("published_parsed"))
    rss_guid = entry.get("id") or entry.get("guid")
    logger.info(
        "db.article.upsert.start feed_id=%s title=%s url=%s guid=%s",
        feed_id,
        entry.get("title"),
        canonical_url,
        rss_guid,
    )

    row = conn.execute(
        """
        WITH inserted AS (
            INSERT INTO news_articles (
                source_feed_id, source_name, title, url, canonical_url, url_hash,
                rss_guid, author, published_at, meta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (url_hash) DO NOTHING
            RETURNING id, TRUE AS inserted, parse_status
        )
        SELECT id, inserted, parse_status FROM inserted
        UNION ALL
        SELECT id, FALSE AS inserted, parse_status
        FROM news_articles
        WHERE url_hash = %s
        LIMIT 1
        """,
        (
            feed_id,
            source_name,
            entry.get("title"),
            raw_url,
            canonical_url,
            url_hash,
            rss_guid,
            entry.get("author"),
            published_at,
            json.dumps(
                {
                    "rss_summary": entry.get("summary"),
                    "rss_tags": [tag.get("term") for tag in entry.get("tags", [])],
                }
            ),
            url_hash,
        ),
    ).fetchone()
    logger.info(
        "db.article.upsert.done article_id=%s inserted=%s parse_status=%s",
        row["id"],
        bool(row["inserted"]),
        row["parse_status"],
    )
    return row["id"], bool(row["inserted"]), row["parse_status"]


def mark_feed_checked(conn: psycopg.Connection, feed_id: int) -> None:
    logger.info("db.feed.mark_checked feed_id=%s", feed_id)
    conn.execute(
        "UPDATE rss_feeds SET last_checked_at = now(), updated_at = now() WHERE id = %s",
        (feed_id,),
    )


def record_parse_attempt(
    conn: psycopg.Connection,
    article_id: int,
    status: str,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO article_parse_attempts (article_id, status, error, finished_at)
        VALUES (%s, %s, %s, now())
        """,
        (article_id, status, error),
    )


def save_parsed_article(
    conn: psycopg.Connection,
    article_id: int,
    parsed: dict[str, Any],
) -> None:
    author = ", ".join(parsed["authors"]) if parsed["authors"] else None
    logger.info(
        "db.article.save_parsed article_id=%s source=%s text_chars=%s",
        article_id,
        parsed["meta"].get("text_source"),
        len(parsed["text"] or ""),
    )
    conn.execute(
        """
        UPDATE news_articles
        SET title = COALESCE(%s, title),
            author = COALESCE(%s, author),
            published_at = COALESCE(%s, published_at),
            parsed_at = now(),
            parse_status = 'parsed',
            parse_error = NULL,
            html = %s,
            text = %s,
            top_image_url = %s,
            meta = meta || %s::jsonb,
            updated_at = now()
        WHERE id = %s
        """,
        (
            parsed["title"],
            author,
            parsed["publish_date"],
            parsed["html"],
            parsed["text"],
            parsed["top_image_url"],
            json.dumps(parsed["meta"]),
            article_id,
        ),
    )


def build_rss_fallback_article(entry: Any, error: Exception) -> dict[str, Any]:
    title = entry.get("title")
    summary = entry.get("summary")
    text_parts = [part for part in [title, summary] if part]

    if not text_parts:
        raise RuntimeError("Article fetch failed and RSS entry has no title or summary")

    logger.info(
        "article.extract.rss_fallback title=%s reason=%s",
        title,
        str(error)[:300],
    )
    return {
        "title": title,
        "text": "\n\n".join(text_parts),
        "html": None,
        "top_image_url": None,
        "authors": [entry.get("author")] if entry.get("author") else [],
        "publish_date": parsed_time_to_datetime(entry.get("published_parsed")),
        "meta": {
            "text_source": "rss_fallback",
            "rss_summary": summary,
            "full_text_error": str(error)[:1000],
        },
    }


def mark_parse_failed(conn: psycopg.Connection, article_id: int, error: Exception) -> None:
    logger.warning(
        "db.article.mark_failed article_id=%s error=%s",
        article_id,
        str(error)[:500],
    )
    conn.execute(
        """
        UPDATE news_articles
        SET parse_status = 'failed',
            parse_error = %s,
            updated_at = now()
        WHERE id = %s
        """,
        (str(error)[:2000], article_id),
    )


def save_ai_analysis(
    conn: psycopg.Connection,
    article_id: int,
    analysis: dict[str, Any],
    settings: Settings,
) -> None:
    logger.info(
        "db.analysis.save article_id=%s model=%s tickers=%s sentiment=%s",
        article_id,
        settings.deepseek_model,
        analysis.get("tickers"),
        analysis.get("market_sentiment"),
    )
    conn.execute(
        """
        INSERT INTO article_ai_analyses (
            article_id, provider, model, tickers, companies, sectors, event_type,
            market_sentiment, market_significance, macroeconomic_themes,
            affected_industries, potential_winners, potential_losers, summary,
            raw_response
        )
        VALUES (%s, 'deepseek', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (article_id, provider, model) DO UPDATE
        SET tickers = EXCLUDED.tickers,
            companies = EXCLUDED.companies,
            sectors = EXCLUDED.sectors,
            event_type = EXCLUDED.event_type,
            market_sentiment = EXCLUDED.market_sentiment,
            market_significance = EXCLUDED.market_significance,
            macroeconomic_themes = EXCLUDED.macroeconomic_themes,
            affected_industries = EXCLUDED.affected_industries,
            potential_winners = EXCLUDED.potential_winners,
            potential_losers = EXCLUDED.potential_losers,
            summary = EXCLUDED.summary,
            raw_response = EXCLUDED.raw_response
        """,
        (
            article_id,
            settings.deepseek_model,
            analysis.get("tickers") or [],
            analysis.get("companies") or [],
            analysis.get("sectors") or [],
            analysis.get("event_type"),
            analysis.get("market_sentiment"),
            analysis.get("market_significance"),
            analysis.get("macroeconomic_themes") or [],
            analysis.get("affected_industries") or [],
            analysis.get("potential_winners") or [],
            analysis.get("potential_losers") or [],
            analysis.get("summary"),
            json.dumps(analysis),
        ),
    )


def analyze_existing_article_if_missing(
    conn: psycopg.Connection,
    article_id: int,
    settings: Settings,
) -> bool:
    row = conn.execute(
        """
        SELECT a.text
        FROM news_articles a
        WHERE a.id = %s
          AND a.text IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM article_ai_analyses ai
              WHERE ai.article_id = a.id
                AND ai.provider = 'deepseek'
                AND ai.model = %s
          )
        """,
        (article_id, settings.deepseek_model),
    ).fetchone()
    if not row:
        return False

    try:
        analysis = analyze_article_text(row["text"], settings)
        save_ai_analysis(conn, article_id, analysis, settings)
        return True
    except Exception as exc:
        logger.exception(
            "analysis.existing.failed article_id=%s error=%s",
            article_id,
            exc,
        )
        return False


def parse_and_analyze_article(
    conn: psycopg.Connection,
    article_id: int,
    url: str,
    entry: Any,
    settings: Settings,
) -> None:
    logger.info("article.pipeline.start article_id=%s url=%s", article_id, url)
    try:
        try:
            parsed = extract_article(url, settings)
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 403:
                raise
            logger.warning(
                "article.extract.requests.forbidden article_id=%s url=%s",
                article_id,
                url,
            )
            if not settings.playwright_fallback_enabled:
                logger.info(
                    "article.extract.playwright.disabled article_id=%s url=%s",
                    article_id,
                    url,
                )
                parsed = build_rss_fallback_article(entry, exc)
            else:
                try:
                    parsed = extract_article_with_playwright(url, settings)
                    if not parsed["text"]:
                        raise RuntimeError("Playwright returned no extractable article text")
                except Exception as playwright_exc:
                    logger.warning(
                        "article.extract.playwright.failed article_id=%s url=%s error=%s",
                        article_id,
                        url,
                        str(playwright_exc)[:500],
                    )
                    parsed = build_rss_fallback_article(entry, playwright_exc)

        if not parsed["text"]:
            raise RuntimeError("Article parser returned no text")

        save_parsed_article(conn, article_id, parsed)
        record_parse_attempt(conn, article_id, "success")
        logger.info(
            "article.pipeline.parsed article_id=%s source=%s",
            article_id,
            parsed["meta"].get("text_source"),
        )
    except Exception as exc:
        mark_parse_failed(conn, article_id, exc)
        record_parse_attempt(conn, article_id, "failed", str(exc)[:2000])
        raise

    if settings.analyze_articles:
        try:
            analysis = analyze_article_text(parsed["text"], settings)
            save_ai_analysis(conn, article_id, analysis, settings)
        except Exception as exc:
            logger.exception("analysis.failed url=%s error=%s", url, exc)


def ingest_feed(conn: psycopg.Connection, feed_url: str, settings: Settings) -> dict[str, int]:
    logger.info("feed.ingest.start url=%s", feed_url)
    feed_response = fetch_url(
        feed_url,
        proxy=settings.proxy_url,
        timeout=settings.request_timeout_seconds,
    )
    parsed_feed = feedparser.parse(feed_response.content)
    feed_name = parsed_feed.feed.get("title") or feed_url
    source_name = parsed_feed.feed.get("title")
    feed_id = ensure_feed(conn, feed_name, feed_url, source_name)
    logger.info(
        "feed.ingest.loaded feed_id=%s name=%s entries=%s",
        feed_id,
        feed_name,
        len(parsed_feed.entries),
    )

    stats = {
        "seen": 0,
        "inserted": 0,
        "duplicates": 0,
        "parsed": 0,
        "analyzed_existing": 0,
        "failed": 0,
    }
    for entry in parsed_feed.entries:
        stats["seen"] += 1
        logger.info(
            "feed.entry.seen feed_id=%s index=%s title=%s url=%s",
            feed_id,
            stats["seen"],
            entry.get("title"),
            entry.get("link"),
        )
        with conn.transaction():
            article_id, inserted, parse_status = upsert_rss_article(
                conn, feed_id, source_name, entry
            )
        if inserted:
            stats["inserted"] += 1
        else:
            stats["duplicates"] += 1

        should_retry_failed = (
            parse_status == "failed" and settings.retry_failed_articles
        )
        if parse_status != "pending" and not should_retry_failed:
            logger.info(
                "feed.entry.skip article_id=%s parse_status=%s reason=not_pending",
                article_id,
                parse_status,
            )
            if settings.analyze_articles and parse_status == "parsed":
                if analyze_existing_article_if_missing(conn, article_id, settings):
                    stats["analyzed_existing"] += 1
            continue
        if should_retry_failed:
            logger.info("feed.entry.retry_failed article_id=%s", article_id)

        article_url = normalize_url(entry["link"])
        try:
            parse_and_analyze_article(conn, article_id, article_url, entry, settings)
            stats["parsed"] += 1
        except Exception as exc:
            stats["failed"] += 1
            logger.exception("article.pipeline.failed url=%s error=%s", article_url, exc)

    with conn.transaction():
        mark_feed_checked(conn, feed_id)
    logger.info("feed.ingest.done url=%s stats=%s", feed_url, stats)
    return stats


def load_enabled_feeds(conn: psycopg.Connection) -> list[str]:
    logger.info("db.feed.load_enabled.start")
    rows = conn.execute(
        """
        SELECT url
        FROM rss_feeds
        WHERE enabled = TRUE
        ORDER BY COALESCE(last_checked_at, '-infinity'::timestamptz), id
        """
    ).fetchall()
    feed_urls = [row["url"] for row in rows]
    logger.info("db.feed.load_enabled.done count=%s", len(feed_urls))
    return feed_urls


def log_database_counts(conn: psycopg.Connection) -> None:
    row = conn.execute(
        """
        SELECT
            (SELECT count(*) FROM rss_feeds) AS feeds,
            (SELECT count(*) FROM news_articles) AS articles,
            (SELECT count(*) FROM news_articles WHERE parse_status = 'parsed') AS parsed_articles,
            (SELECT count(*) FROM news_articles WHERE parse_status = 'failed') AS failed_articles,
            (SELECT count(*) FROM article_ai_analyses) AS analyses
        """
    ).fetchone()
    logger.info(
        "db.counts feeds=%s articles=%s parsed_articles=%s failed_articles=%s analyses=%s",
        row["feeds"],
        row["articles"],
        row["parsed_articles"],
        row["failed_articles"],
        row["analyses"],
    )


def ingest_feeds(settings: Settings, feed_urls: list[str] | None = None) -> None:
    logger.info(
        "run.start analyze_articles=%s retry_failed=%s playwright_fallback=%s",
        settings.analyze_articles,
        settings.retry_failed_articles,
        settings.playwright_fallback_enabled,
    )
    with psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
        autocommit=True,
    ) as conn:
        feed_urls = feed_urls or load_enabled_feeds(conn)
        if not feed_urls:
            logger.warning("run.no_enabled_feeds")
            return

        for feed_url in feed_urls:
            stats = ingest_feed(conn, feed_url, settings)
            logger.info("run.feed.done url=%s stats=%s", feed_url, stats)
        log_database_counts(conn)
    logger.info("run.done")


def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    parser = argparse.ArgumentParser(description="RSS article ingestion worker")
    parser.add_argument(
        "--feed",
        action="append",
        help=(
            "Optional RSS feed URL override. If omitted, enabled feeds are read "
            "from the rss_feeds table."
        ),
    )
    args = parser.parse_args()
    ingest_feeds(settings, args.feed)


if __name__ == "__main__":
    main()
