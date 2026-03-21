"""Controller layer for the legal transcript workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from depo_formatter.app_logging import get_logger
from depo_formatter.file_loader import LoadedTranscript, load_transcript
from depo_formatter.formatter import format_transcript

from transcript_formatter.app.services.ai_service import AICorrectionService
from transcript_formatter.app.services.export_service import ExportOptions, TranscriptExportService
from transcript_formatter.app.services.transcript_parser import infer_witness_name, parse_transcript_text, render_entries

LOGGER = get_logger(__name__)


@dataclass
class WorkflowState:
    loaded_file_path: str | None = None
    loaded_transcript: LoadedTranscript | None = None
    source_text: str = ""
    ai_text: str = ""
    formatted_text: str = ""
    transcript_entries: list[dict[str, str]] = field(default_factory=list)
    ai_completed: bool = False
    formatting_applied: bool = False
    last_export_path: str | None = None


class WorkflowController:
    """Orchestrate transcript load, AI, formatting, and export steps."""

    def __init__(self) -> None:
        self.state = WorkflowState()
        self._ai_service = AICorrectionService()
        self._export_service = TranscriptExportService()

    def load_file(self, file_path: str) -> str:
        loaded = load_transcript(file_path)
        transcript = loaded.text.strip()
        if not transcript:
            raise ValueError("The selected file did not contain extractable transcript text.")

        self.state = WorkflowState(
            loaded_file_path=file_path,
            loaded_transcript=loaded,
            source_text=transcript,
        )
        LOGGER.info("Loaded transcript file: %s", file_path)
        return transcript

    def run_ai_correction(self, proper_nouns: list[str], dash_style: str) -> str:
        if not self.state.source_text.strip():
            raise ValueError("Load a transcript before running AI correction.")

        corrected = self._ai_service.run_legal_correction(
            self.state.source_text,
            proper_nouns=proper_nouns,
            dash_style=dash_style,
        )
        self.state.ai_text = corrected
        self.state.ai_completed = True
        self.state.formatting_applied = False
        self.state.transcript_entries = []
        self.state.formatted_text = ""
        return corrected

    def apply_formatting(self) -> str:
        if not self.state.ai_completed:
            raise ValueError("Run AI correction before applying UFM formatting.")

        source_text = self.state.ai_text.strip()
        if not source_text:
            raise ValueError("There is no AI-corrected transcript to format.")

        normalized = format_transcript(source_text, use_qa_format=True, remove_fillers=False)
        entries = parse_transcript_text(normalized)
        if not entries:
            raise ValueError("No transcript entries were produced during formatting.")

        preview_text = render_entries(entries)
        self.state.formatted_text = preview_text
        self.state.transcript_entries = entries
        self.state.formatting_applied = True
        LOGGER.info("Formatting end: %s transcript entries", len(entries))
        return preview_text

    def export_draft(
        self,
        header_text: str,
        footer_text: str,
        show_line_numbers: bool,
        show_header: bool,
        show_footer: bool,
    ) -> str:
        return self._export(
            output_name="transcript_draft.docx",
            options=ExportOptions(
                show_format_box=False,
                show_line_numbers=show_line_numbers,
                show_header=show_header,
                show_footer=show_footer,
                header_text=header_text,
                footer_text=footer_text,
            ),
        )

    def export_final(
        self,
        header_text: str,
        footer_text: str,
        show_line_numbers: bool,
        show_header: bool,
        show_footer: bool,
    ) -> str:
        return self._export(
            output_name="transcript_final.docx",
            options=ExportOptions(
                show_format_box=True,
                show_line_numbers=show_line_numbers,
                show_header=show_header,
                show_footer=show_footer,
                header_text=header_text,
                footer_text=footer_text,
            ),
        )

    def status_snapshot(self) -> tuple[str, str, str]:
        ai_status = "AI Completed" if self.state.ai_completed else "AI Not Run"
        formatting_status = "Formatting Applied" if self.state.formatting_applied else "Formatting Not Applied"
        finalization_status = (
            f"Finalization Applied: {Path(self.state.last_export_path).name}"
            if self.state.last_export_path
            else "Finalization Not Applied"
        )
        return ai_status, formatting_status, finalization_status

    def _export(self, output_name: str, options: ExportOptions) -> str:
        if not self.state.formatting_applied or not self.state.transcript_entries:
            raise ValueError("Apply UFM formatting before export.")

        witness_name = infer_witness_name(
            self.state.loaded_file_path,
            self.state.formatted_text or self.state.ai_text or self.state.source_text,
        )
        output_path = Path("output") / output_name
        export_path = self._export_service.export_document(
            transcript_entries=self.state.transcript_entries,
            output_path=str(output_path),
            witness_name=witness_name,
            options=options,
        )
        self.state.last_export_path = export_path
        return export_path
