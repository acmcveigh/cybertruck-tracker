"""Small, dependency-free parsing helpers shared by the data sources.

APIs return inconsistent shapes (nested objects, strings where you expect
numbers, 1/0 for booleans). These helpers parse defensively so a single odd
field never crashes a whole run.
"""
from __future__ import annotations

from typing import Any, Optional


def dig(d: dict, *paths: str, default: Any = None) -> Any:
    """Return the first present value among dotted paths.

    Example: dig(item, "build.year", "year") tries item["build"]["year"]
    first, then item["year"], else `default`.
    """
    for path in paths:
        cur: Any = d
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur and cur[part] is not None:
                cur = cur[part]
            else:
                ok = False
                break
        if ok:
            return cur
    return default


def to_int(v: Any) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None


def to_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return round(float(v), 1)
    except (ValueError, TypeError):
        return None


def as_bool(v: Any) -> Optional[bool]:
    """Parse 1/0, true/false, yes/no. Returns None when unknown."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    return None


def title_status_clean(v: Any) -> Optional[bool]:
    """Interpret a free-text title-status string. None = unknown."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    bad = ("salvage", "rebuilt", "rebuild", "branded", "lemon",
           "flood", "junk", "total", "parts")
    if any(b in s for b in bad):
        return False
    if "clean" in s:
        return True
    return None


def first_in(d: dict, *paths: str) -> str:
    """First element of the first list found among dotted paths (e.g. photos)."""
    for path in paths:
        arr = dig(d, path)
        if isinstance(arr, list) and arr:
            return str(arr[0])
    return ""
