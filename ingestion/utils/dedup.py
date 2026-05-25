from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAMS = frozenset({
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref",
    "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term",
})


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        [
            (k, v)
            for k, v in sorted(parse_qsl(parts.query, keep_blank_values=True))
            if k.lower() not in _TRACKING_PARAMS
        ],
        doseq=True,
    )
    return urlunsplit((
        parts.scheme.lower() or "https",
        parts.netloc.lower(),
        parts.path or "/",
        query,
        "",
    ))


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()
