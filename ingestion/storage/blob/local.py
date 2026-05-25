from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalFilesystemBlob:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    async def put(self, key: str, data: bytes, metadata: dict[str, str] | None = None) -> None:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        logger.info("blob.local.put key=%s bytes=%s", key, len(data))

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread((self._root / key).exists)
