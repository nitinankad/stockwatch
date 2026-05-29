from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from shared.models.news import RawNewsItem
from shared.models.ohlcv import OHLCVBar


@runtime_checkable
class NewsSource(Protocol):
    name: str

    def fetch(self) -> AsyncIterator[RawNewsItem]: ...


@runtime_checkable
class OHLCVSource(Protocol):
    def poll(self, symbols: list[str]) -> AsyncIterator[OHLCVBar]: ...
