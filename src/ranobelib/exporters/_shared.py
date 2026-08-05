"""Helpers shared between exporter implementations (not part of the public Exporter protocol)."""

from __future__ import annotations

from ranobelib.models import Chapter


def chapter_heading(chapter: Chapter) -> str:
    """A human-readable "Volume X, Chapter Y[: Name]" heading for ``chapter``."""
    heading = f"Volume {chapter.volume}, Chapter {chapter.number}"
    return f"{heading}: {chapter.name}" if chapter.name else heading
