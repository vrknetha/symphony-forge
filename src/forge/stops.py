"""Stub seam for owner stops and desktop notices (implemented in STOPS)."""
from __future__ import annotations

from pathlib import Path


def stopped(top: Path, item: str) -> bool:
    """Whether the owner has stopped this item."""
    return False


def lift(top: Path, item: str) -> None:
    """Clear the owner's stop when a person runs forge land on this item."""


def add(top: Path, item: str) -> None:
    """Record that the owner stopped this item."""


def ended(top: Path, item: str, code: int, lines: list[str]) -> None:
    """Record that an item stopped and needs the owner."""


def summary(top: Path, merged: list[str]) -> None:
    """Send the end-of-run summary notice for a repo the runner worked on."""
