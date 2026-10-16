"""Compression and truncation utilities for tool outputs to prevent context overflow."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union


def compress_string(text: str, max_chars: int = 4000, head_ratio: float = 0.7) -> str:
    """Compress long string by retaining head and tail with a truncation marker."""
    if len(text) <= max_chars:
        return text

    head_chars = int(max_chars * head_ratio)
    tail_chars = max_chars - head_chars
    marker = f"\n\n... [Output truncated: original size {len(text)} chars, limited to {max_chars} chars] ...\n\n"

    # Ensure marker fits
    available = max_chars - len(marker)
    if available <= 0:
        return text[:max_chars]

    head_part = text[: int(available * head_ratio)]
    tail_part = text[-int(available * (1 - head_ratio)) :] if tail_chars > 0 else ""
    return f"{head_part}{marker}{tail_part}"


def prune_empty_fields(data: Any) -> Any:
    """Recursively remove None values and empty collections from dictionaries to reduce JSON size."""
    if isinstance(data, dict):
        return {
            k: prune_empty_fields(v)
            for k, v in data.items()
            if v is not None and v != "" and v != [] and v != {}
        }
    elif isinstance(data, list):
        return [prune_empty_fields(item) for item in data if item is not None]
    return data


def compress_json(
    data: Any,
    max_chars: int = 4000,
    max_list_items: int = 15,
    max_string_len: int = 600,
    prune_empty: bool = True,
) -> Any:
    """Compress JSON-like data structures (dicts, lists) to fit within context budget.
    
    Strategies:
    1. Prune null and empty values.
    2. Truncate oversized string fields inside records.
    3. Truncate long lists to max_list_items, appending summary metadata.
    4. Ensure output serialized size is within max_chars.
    """
    if prune_empty and isinstance(data, (dict, list)):
        data = prune_empty_fields(data)

    def _truncate_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                new_dict[k] = _truncate_recursive(v)
            return new_dict
        elif isinstance(obj, list):
            if len(obj) > max_list_items:
                truncated_list = [_truncate_recursive(item) for item in obj[:max_list_items]]
                truncated_list.append({
                    "_meta_compression": True,
                    "total_items": len(obj),
                    "retained_items": max_list_items,
                    "truncated_items": len(obj) - max_list_items,
                    "notice": f"Truncated {len(obj) - max_list_items} items to fit context window.",
                })
                return truncated_list
            return [_truncate_recursive(item) for item in obj]
        elif isinstance(obj, str):
            if len(obj) > max_string_len:
                return obj[:max_string_len] + f"... [truncated {len(obj) - max_string_len} chars]"
            return obj
        return obj

    truncated = _truncate_recursive(data)

    # Check serialized size
    try:
        serialized = json.dumps(truncated, default=str)
        if len(serialized) > max_chars:
            # If still exceeds max_chars, perform string compression on the serialized JSON
            compressed_str = compress_string(serialized, max_chars=max_chars)
            # Try to return valid structure if possible, otherwise compressed string representation
            try:
                return json.loads(compressed_str)
            except Exception:
                return compressed_str
    except Exception:
        pass

    return truncated


def compress_tool_output(
    output: Any,
    max_chars: int = 4000,
    max_list_items: int = 15,
    max_string_len: int = 600,
) -> Any:
    """Universal compression entrypoint for any tool output (str, dict, list, primitive)."""
    if output is None:
        return None

    if isinstance(output, str):
        return compress_string(output, max_chars=max_chars)

    if isinstance(output, (dict, list)):
        return compress_json(
            output,
            max_chars=max_chars,
            max_list_items=max_list_items,
            max_string_len=max_string_len,
        )

    # Fallback for other objects
    str_repr = str(output)
    if len(str_repr) > max_chars:
        return compress_string(str_repr, max_chars=max_chars)
    return output
