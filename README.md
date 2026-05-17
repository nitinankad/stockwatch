# stockwatch
An AI/ML powered stock screener where it ingests news articles in semi-realtime and analyzes them for potential stock plays, sentiment, etc

## RSS ingestion

This first slice ingests RSS feeds into Postgres, extracts full article text, and optionally sends the article text to an OpenAI-compatible AI provider such as DeepSeek.

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

Run ingestion:

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

You can also bulk insert feeds with the helper script. Edit the `RSS_FEEDS` list in `scripts/rss_feeds.py`, or pass a text file with one URL per line:

```powershell
python scripts/rss_feeds.py --file feeds.txt
```

CSV files are supported with `url,name,source_name` columns.

For one-off testing, you can still pass feed URLs directly:

```powershell
python ingestion/ingestion_main.py --feed "https://finance.yahoo.com/news/rssindex"
```
