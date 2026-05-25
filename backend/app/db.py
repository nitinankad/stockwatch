from __future__ import annotations

from typing import AsyncIterator

import psycopg
import psycopg.rows
from fastapi import HTTPException

from app.core.config import settings


async def get_conn() -> AsyncIterator[psycopg.AsyncConnection]:
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database not configured")
    async with await psycopg.AsyncConnection.connect(
        settings.database_url,
        row_factory=psycopg.rows.dict_row,
    ) as conn:
        yield conn
