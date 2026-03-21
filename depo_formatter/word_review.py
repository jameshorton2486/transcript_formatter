"""
word_review.py — Microsoft Word Track Changes integration.

FIXES vs. original:
  FIX-1  Windows guard: win32com and pythoncom are imported lazily inside
         open_word_with_track_changes(). The module no longer crashes on
         import when running on macOS or Linux.
  FIX-2  Clear platform error: raises RuntimeError with a helpful message
         when called on non-Windows, instead of ImportError on import.
  FIX-3  Tab stop positions: uses Inches() values aligned with UFM tab stops
         (Tab1=0.5", Tab2=1.0", Tab3=1.5") instead of arbitrary manual math.
  FIX-4  Paragraph count guard: if Word paragraph count doesn't match line
         count, raises a clear error instead of silently skipping lines.
"""

import platform
import sys
from pathlib import Path

from app_logging import get_logger

LOGGER = get_logger(__name__)

# UFM tab stops in points (1 inch = 72 points)
_TAB1_PT = 0.5 * 72   # 36pt  — Q./A. label
_TAB2_PT = 1.0 * 72   # 72pt  — text after Q./A.
_TAB3_PT = 1.5 * 72   # 108pt — colloquy / parentheticals
_CENTER_PT = 3.25 * 72 # 234pt — center tab


def _require_windows() -> None:
    """Raise a clear error if not running on Windows."""
    if platform.system() != "Windows":
        raise RuntimeError(
            "Word Track Changes review requires Microsoft Word and pywin32.\n"
            "This feature is only available on Windows.\n"
            f"Current platform: {platform.system()} {platform.release()}"
        )


def normalize_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def is_protected_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith(("Q.", "A.")):
        return True
    if stripped.startswith(("MR.", "MS.", "MRS.", "THE WITNESS", "THE REPORTER")):
        return True
    return False


def apply_tab_stops(paragraph) -> None:
    """Apply UFM-aligned tab stops to a Word paragraph object."""
    try:
        tab_stops = paragraph.Range.ParagraphFormat.TabStops
        # Clear existing tab stops (iterate backwards — Word COM requirement)
        for i in range(tab_stops.Count, 0, -1):
            tab_stops(i).Clear()
        # Set UFM tab stops
        tab_stops.Add(Position=_TAB1_PT)
        tab_stops.Add(Position=_TAB2_PT)
        tab_stops.Add(Position=_TAB3_PT)
        tab_stops.Add(Position=_CENTER_PT, Alignment=1)  # 1 = wdAlignTabCenter
    except Exception:
        LOGGER.exception("Failed to apply Word tab stops to paragraph")


def derive_review_output_path(loaded_file_path: str | None) -> str:
    if loaded_file_path:
        src = Path(loaded_file_path)
        return str(src.with_name(f"{src.stem}_review.docx"))
    return str((Path.cwd() / "review_output_review.docx").resolve())


def open_word_with_track_changes(
    original_text: str,
    corrected_text: str,
    output_path: str,
) -> str:
    """
    Open Microsoft Word, populate it with original_text, then apply
    corrected_text line-by-line with Track Changes enabled.

    Raises:
        RuntimeError — on non-Windows platforms (FIX-1)
        ValueError   — if line counts don't match or protected labels changed
        Exception    — propagated from pywin32 on Word errors
    """
    # FIX-1: lazy Windows guard
    _require_windows()

    # FIX-1: lazy import — only reaches here on Windows
    import pythoncom
    import win32com.client

    original_lines  = normalize_lines(original_text)
    corrected_lines = normalize_lines(corrected_text)

    if len(original_lines) != len(corrected_lines):
        raise ValueError(
            f"Original ({len(original_lines)} lines) and corrected "
            f"({len(corrected_lines)} lines) transcripts must have the same "
            "number of lines for Track Changes review."
        )

    LOGGER.info("Starting Word Track Changes process (%s lines)", len(original_lines))

    pythoncom.CoInitialize()
    word = None

    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = True

        doc = word.Documents.Add()
        doc.Content.Text = "\r".join(original_lines)
        doc.TrackRevisions = True

        paragraph_count = doc.Paragraphs.Count

        # Apply tab stops to all paragraphs
        for i in range(1, paragraph_count + 1):
            apply_tab_stops(doc.Paragraphs(i))

        # Apply line-by-line diffs
        for idx, (orig_line, corr_line) in enumerate(
            zip(original_lines, corrected_lines), start=1
        ):
            if orig_line == corr_line:
                continue

            # FIX-4: explicit bounds check
            if idx > paragraph_count:
                raise ValueError(
                    f"Word document has {paragraph_count} paragraphs but "
                    f"transcript has {len(original_lines)} lines. "
                    "They must match for Track Changes review."
                )

            if is_protected_line(orig_line) and orig_line.strip() != corr_line.strip():
                raise ValueError(
                    f"Protected label on line {idx} would be modified. "
                    "Q./A. and speaker label lines cannot be changed in Word review."
                )

            paragraph_range = doc.Paragraphs(idx).Range
            paragraph_range.Text = corr_line + "\r"
            apply_tab_stops(doc.Paragraphs(idx))

        destination = Path(output_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        doc.SaveAs(str(destination))

        LOGGER.info("Saved Word review document: %s", destination)
        return str(destination)

    except Exception:
        LOGGER.exception("Word Track Changes process failed")
        raise
    finally:
        pythoncom.CoUninitialize()
