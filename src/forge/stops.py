"""Stub seam for owner stops and desktop notices (implemented in STOPS)."""
from __future__ import annotations

from pathlib import Path


def stopped(top: Path, item: str) -> bool:
    """Whether the owner has stopped this item."""
    return False


def require_running(top: Path, item: str) -> None:
    """Refuse when the owner has stopped this item."""


def ended(top: Path, item: str, reason: str, *, next_step: str = "", url: str = "") -> None:
    """Record that an item stopped and needs the owner."""
