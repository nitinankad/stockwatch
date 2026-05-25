from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator

import httpx

from ingestion.models.ohlcv import OHLCVBar

logger = logging.getLogger(__name__)

_BASE_URL = "https://data.alpaca.markets/v2/stocks/bars"


class AlpacaOHLCVSource:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timeframe: str = "1Min",
        timeout: int = 30,
    ) -> None:
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        self._timeframe = timeframe
        self._timeout = timeout

    async def poll(self, symbols: list[str]) -> AsyncIterator[OHLCVBar]:
        if not symbols:
            return

        params = {
            "symbols": ",".join(symbols),
            "timeframe": self._timeframe,
            "limit": 10,
            "sort": "desc",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            logger.info("alpaca_ohlcv.poll symbols=%s timeframe=%s", symbols, self._timeframe)
            try:
                response = await client.get(_BASE_URL, headers=self._headers, params=params)
                response.raise_for_status()
            except Exception as exc:
                logger.warning("alpaca_ohlcv.poll.error error=%s", exc)
                return

            for ticker, bars in response.json().get("bars", {}).items():
                for bar in bars:
                    yield OHLCVBar(
                        ticker=ticker,
                        open=Decimal(str(bar["o"])),
                        high=Decimal(str(bar["h"])),
                        low=Decimal(str(bar["l"])),
                        close=Decimal(str(bar["c"])),
                        volume=int(bar["v"]),
                        timestamp=datetime.fromisoformat(bar["t"].replace("Z", "+00:00")),
                        timeframe=self._timeframe,
                    )
