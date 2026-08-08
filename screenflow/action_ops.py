"""Canonical action op names used by editors and validation."""

from __future__ import annotations

COMMON_OPS = (
    "click",
    "key",
    "wait",
    "hold_key",
    "macro",
)
ADVANCED_OPS = (
    "set_var",
    "clear_var",
    "script",
)
OPS = COMMON_OPS + ADVANCED_OPS
