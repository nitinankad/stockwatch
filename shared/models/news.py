from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RawNewsItem(BaseModel):
    url: str
    canonical_url: str
    url_hash: str
    title: str | None
    source: str
    published_at: datetime | None
    raw_payload: dict[str, Any]
