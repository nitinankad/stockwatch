from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from psycopg.rows import dict_row


@asynccontextmanager
async def connect(database_url: str) -> AsyncIterator[psycopg.AsyncConnection]:
    async with await psycopg.AsyncConnection.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:
        yield conn
