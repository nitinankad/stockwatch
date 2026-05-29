from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from backfill.config import Settings
from backfill.service import BackfillService
from fundamentals.loader import FundamentalsCache
from shared.alpaca import AlpacaClient
from shared.logging import configure

_EDGAR_DIR = Path(__file__).parent.parent / "data" / "edgar"


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    load_dotenv()
    settings = Settings()
    configure(settings.log_level)

    if not settings.database_url:
        raise SystemExit("DATABASE_URL is required")
    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        raise SystemExit("ALPACA_API_KEY and ALPACA_API_SECRET are required")
    if not settings.backfill_symbols:
        raise SystemExit("BACKFILL_SYMBOLS is required (comma-separated tickers)")

    fundamentals = FundamentalsCache(_EDGAR_DIR) if _EDGAR_DIR.exists() else None

    service = BackfillService(
        alpaca=AlpacaClient(settings.alpaca_api_key, settings.alpaca_api_secret),
        database_url=settings.database_url,
        symbols=settings.backfill_symbols,
        timeframe=settings.ohlcv_timeframe,
        sample_interval=settings.sample_interval_minutes,
        prediction_horizons=settings.prediction_horizons,
        max_workers=settings.backfill_workers,
        fundamentals=fundamentals,
    )
    asyncio.run(service.run(settings.start_dt(), settings.end_dt()))


if __name__ == "__main__":
    main()
