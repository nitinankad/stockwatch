# stockwatch
An AI/ML powered stock screener where it ingests news articles in semi-realtime and analyzes them for potential stock plays, sentiment, etc

## Raw news ingestion

The raw ingestion slice polls news sources, deduplicates articles, and writes raw article envelopes through a storage adapter. The service depends on `BlobStorage`, `NewsSource`, and `ArticleRegistry` ports, so Cloudflare R2, S3, Postgres, Redis, or queue notifications can be added without changing the ingestion orchestration.

The current concrete adapters are:

- RSS feeds via HTTP.
- Alpaca news via HTTP when enabled.
- Local filesystem blob storage for development.
- JSON file dedupe registry for development.

Run one ingestion cycle with local blob storage:

```powershell
$env:INGESTION_RSS_FEEDS="https://finance.yahoo.com/news/rssindex"
python ingestion/ingestion_main.py --once
```

Run continuously, polling every minute by default:

```powershell
python scripts/rss_ingestion.py
```

For one-off testing, you can pass feed URLs directly:

```powershell
python ingestion/ingestion_main.py --once --feed "https://finance.yahoo.com/news/rssindex"
```

Raw envelopes are written under `INGESTION_LOCAL_BLOB_ROOT` using date/source prefixes. Dedupe state is written to `INGESTION_STATE_PATH`.

The storage boundary is `ingestion.ports.BlobStorage`. To swap Cloudflare R2 for S3 later, add a new adapter implementing `put_json(key, payload, content_type=...)` and select it from `ingestion.factory.build_service`.

## RSS analysis prototype

The older prototype in `scripts/rss_ingestion.py` ingests RSS feeds into Postgres, extracts full article text, and optionally sends the article text to an OpenAI-compatible AI provider such as DeepSeek.

### Data model

- `rss_feeds`: feed registry and last checked timestamp.
- `news_articles`: one row per canonical article URL. `url_hash` is unique so the same URL is not parsed twice.
- `article_parse_attempts`: history of parse successes/failures for observability.
- `article_ai_analyses`: structured sentiment and stock-play extraction. Unique by `article_id`, provider, and model.

Apply the schema:

```powershell
psql $env:DATABASE_URL -f db/schema.sql
```

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Configure environment variables from `.env.example`. Do not hardcode API keys or proxy credentials in source code.

Use `LOG_LEVEL=INFO` for normal ingestion step logs, or `LOG_LEVEL=WARNING` for quieter output.

If you change proxy/header settings and want to retry rows already marked `failed`, set:

```powershell
$env:RETRY_FAILED_ARTICLES="true"
```

Some publishers block scripted full-text downloads with 403 responses. For those, ingestion tries a lightweight headless Chromium fallback through Playwright, using the same `HTTP_PROXY_URL` / `PROXY_URL` setting. If that still fails, it stores the RSS title/summary as a fallback and records `meta.text_source = "rss_fallback"`.

Run the prototype:

```powershell
$env:DATABASE_URL="postgresql://stockwatch:stockwatch@localhost:5432/stockwatch"
$env:DEEPSEEK_API_KEY="..."
python ingestion/ingestion_main.py
```

Feeds are read from enabled rows in `rss_feeds`:

```sql
INSERT INTO rss_feeds (name, url, source_name)
VALUES ('Yahoo Finance', 'https://finance.yahoo.com/news/rssindex', 'Yahoo Finance');
```

You can also bulk insert feeds with the helper script. Edit the `RSS_FEEDS` list in `scripts/add_rss_feeds.py`, or pass a text file with one URL per line:

```powershell
python scripts/add_rss_feeds.py --file feeds.txt
```

CSV files are supported with `url,name,source_name` columns.

For one-off testing, you can still pass feed URLs directly:

```powershell
python scripts/rss_ingestion.py --feed "https://finance.yahoo.com/news/rssindex"
```
