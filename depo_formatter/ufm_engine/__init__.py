"""Unified Formatting Module package.

This package contains the modular components used to render transcript-driven
Word templates, register available templates, merge generated DOCX content, and
share typed data contracts across the formatting pipeline.
"""

from .data_models import MergeResult, RenderRequest, TemplateDefinition
from .docx_merger import DocxMerger
from .template_registry import TemplateRegistry
from .template_renderer import TemplateRenderer

__all__ = [
    "DocxMerger",
    "MergeResult",
    "RenderRequest",
    "TemplateDefinition",
    "TemplateRegistry",
    "TemplateRenderer",
]
