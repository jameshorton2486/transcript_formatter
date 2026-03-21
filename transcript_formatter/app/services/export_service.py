"""DOCX export service for draft and final transcript output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from depo_formatter.app_logging import get_logger
from depo_formatter.ufm_engine.document_builder import DocumentBuilder

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class ExportOptions:
    show_format_box: bool
    show_line_numbers: bool
    show_header: bool
    show_footer: bool
    header_text: str
    footer_text: str


class TranscriptExportService:
    """Generate UFM-compliant draft and final DOCX output."""

    def __init__(self) -> None:
        self._builder = DocumentBuilder()

    def export_document(
        self,
        transcript_entries: list[dict[str, str]],
        output_path: str,
        witness_name: str,
        options: ExportOptions,
    ) -> str:
        if not transcript_entries:
            raise ValueError("No formatted transcript entries are available for export.")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        LOGGER.info("Formatting start: export build for %s", output_file)
        self._builder.build_transcript_body(
            transcript_entries,
            show_line_numbers=options.show_line_numbers,
            show_format_box=options.show_format_box,
        )
        document = self._builder._transcript_body_document
        self._builder.finalize_transcript_document(
            document,
            job_data={
                "witness_name": witness_name,
                "date": date.today().isoformat(),
                "reporter_name": "Court Reporter",
                "csr_number": "CSR-0000",
            },
            finalization_options={
                "show_format_box": options.show_format_box,
                "show_line_numbers": options.show_line_numbers,
                "show_header": options.show_header,
                "show_footer": options.show_footer,
                "header_text": options.header_text,
                "footer_text": options.footer_text,
            },
        )
        document.save(str(output_file))
        LOGGER.info("Export success: %s", output_file)
        return str(output_file)
