"""AI correction workflow service."""

from __future__ import annotations

from depo_formatter.ai_tools import run_ai_tool
from depo_formatter.app_logging import get_logger

from .transcript_parser import unwrap_qa_blocks, wrap_qa_blocks_for_ai

LOGGER = get_logger(__name__)


class AICorrectionService:
    """Run transcript correction through the constrained AI pipeline."""

    def run_legal_correction(
        self,
        transcript_text: str,
        proper_nouns: list[str] | None = None,
        dash_style: str = "double-hyphen",
    ) -> str:
        LOGGER.info("AI processing start")
        wrapped_text = wrap_qa_blocks_for_ai(transcript_text)
        result = run_ai_tool(
            wrapped_text,
            proper_nouns=proper_nouns,
            dash_style=dash_style,
        )
        cleaned = unwrap_qa_blocks(result)
        LOGGER.info("AI processing end")
        return cleaned
