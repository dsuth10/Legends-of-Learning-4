"""Reusable query utilities (pagination, future eager-load helpers).

Note: Relationships declared with ``lazy='dynamic'`` cannot use ``selectinload``;
switch those relationships to ``lazy='select'`` (or use explicit queries) before
adding eager-load helpers here.
"""

from __future__ import annotations


def clamp_page(page: int | None, default: int = 1, max_page: int = 10_000) -> int:
    if page is None:
        return default
    try:
        p = int(page)
    except (TypeError, ValueError):
        return default
    return max(1, min(p, max_page))
