"""DOCX merge coordination for UFM.

This module will assemble multiple rendered DOCX outputs into a single final
document while preserving document order and formatting rules.
"""

from __future__ import annotations

from .data_models import MergeResult


class DocxMerger:
    """Coordinates future DOCX merge operations."""

    def merge(self, source_paths: list[str], output_path: str) -> MergeResult:
        """Merge multiple DOCX files into one output document.

        Placeholder implementation. Merge logic will be added in a later step.
        """
        raise NotImplementedError("DOCX merging is not implemented yet.")
