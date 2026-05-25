from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

import httpx

from shared.models.ohlcv import OHLCVBar

logger = logging.getLogger(__name__)

_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"


class AlpacaClient:
    """Minimal async Alpaca Markets data client with pagination support."""

    def __init__(self, api_key: str, api_secret: str, timeout: int = 30) -> None:
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        self._timeout = timeout

    async def get_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Min",
    ) -> dict[str, list[OHLCVBar]]:
        """Fetch all bars for the given symbols and time range, handling pagination."""
        result: dict[str, list[OHLCVBar]] = {s: [] for s in symbols}
        next_page_token: str | None = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                params: dict = {
                    "symbols": ",".join(symbols),
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "timeframe": timeframe,
                    "limit": 10_000,
                    "sort": "asc",
                    "adjustment": "raw",
                }
                if next_page_token:
                    params["page_token"] = next_page_token

                resp = await client.get(_BARS_URL, headers=self._headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                for ticker, bars in data.get("bars", {}).items():
                    result.setdefault(ticker, []).extend(
                        OHLCVBar(
                            ticker=ticker,
                            open=Decimal(str(b["o"])),
                            high=Decimal(str(b["h"])),
                            low=Decimal(str(b["l"])),
                            close=Decimal(str(b["c"])),
                            volume=int(b["v"]),
                            timestamp=datetime.fromisoformat(b["t"].replace("Z", "+00:00")),
                            timeframe=timeframe,
                        )
                        for b in bars
                    )

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

        logger.info(
            "alpaca.get_bars symbols=%s counts=%s",
            symbols,
            {k: len(v) for k, v in result.items()},
        )
        return result
