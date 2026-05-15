from datetime import datetime, timezone
from typing import Any


def get_utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_number(num: int) -> str:
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def truncate_string(s: str, max_len: int = 50) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."
