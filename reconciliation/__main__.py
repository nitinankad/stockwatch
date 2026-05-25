from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from reconciliation.config import Settings
from reconciliation.service import ReconciliationService
from shared.alpaca import AlpacaClient
from shared.logging import configure


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

    service = ReconciliationService(
        alpaca=AlpacaClient(settings.alpaca_api_key, settings.alpaca_api_secret),
        database_url=settings.database_url,
    )
    asyncio.run(service.run())


if __name__ == "__main__":
    main()
