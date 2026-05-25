from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStorage(Protocol):
    async def put(self, key: str, data: bytes, metadata: dict[str, str] | None = None) -> None: ...
    async def exists(self, key: str) -> bool: ...
