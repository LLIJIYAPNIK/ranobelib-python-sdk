"""Exporter protocol and format registry.

A new export format is a new module in this package: define a class implementing
``Exporter`` and decorate it with ``@register`` — no changes needed here or in ``sdk.py``.
Every module in this package is auto-imported below so its ``@register`` runs on its own.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import ClassVar, Protocol, TypeVar, runtime_checkable

from ranobelib.models import Chapter, Title


@runtime_checkable
class Exporter(Protocol):
    """Renders a title's chapters to a single file in some format."""

    format: ClassVar[str]
    """The registry key this exporter is selected by, e.g. ``"txt"``."""

    def export(self, title: Title, chapters: list[Chapter], output_path: Path) -> Path:
        """Write ``chapters`` (in the given order) to ``output_path``.

        Args:
            title: The chapters' parent title, for metadata (name, authors, ...).
            chapters: The chapters to include, in the order they should appear.
            output_path: Where to write the exported file.

        Returns:
            ``output_path``, once the file has been written.
        """
        ...


ExporterT = TypeVar("ExporterT", bound=type[Exporter])

EXPORTERS: dict[str, type[Exporter]] = {}
"""Registered exporters, keyed by ``Exporter.format``."""


def register(exporter: ExporterT) -> ExporterT:
    """Class decorator: register ``exporter`` under its ``format`` key."""
    EXPORTERS[exporter.format] = exporter
    return exporter


for _module_info in pkgutil.iter_modules(__path__, f"{__name__}."):
    importlib.import_module(_module_info.name)
