import json
from typing import Any, Callable


def extract_json_value(
    raw: str,
    *,
    expected_type: type | tuple[type, ...] | None = None,
    predicate: Callable[[Any], bool] | None = None,
) -> Any | None:
    """Return the first valid JSON value embedded in a model response."""
    text = str(raw or "").strip()
    if not text:
        return None

    decoder = json.JSONDecoder(strict=False)
    for start, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            data, _ = decoder.raw_decode(text[start:])
        except (json.JSONDecodeError, ValueError):
            continue
        if expected_type is not None and not isinstance(data, expected_type):
            continue
        if predicate is not None and not predicate(data):
            continue
        return data
    return None


def extract_json_object(
    raw: str,
    *,
    predicate: Callable[[Any], bool] | None = None,
) -> dict[str, Any] | None:
    data = extract_json_value(raw, expected_type=dict, predicate=predicate)
    return data if isinstance(data, dict) else None
