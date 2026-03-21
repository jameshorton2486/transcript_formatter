"""Transcript parsing, marker wrapping, and preview rendering helpers."""

from __future__ import annotations

import re
from pathlib import Path

QA_PATTERN = re.compile(r"^\s*([QA])\.\s*(.*)$", re.IGNORECASE)
COLLOQUY_PATTERN = re.compile(r"^\s*((?:MR|MS|MRS|DR)\.\s+[A-Z][A-Z '\.-]*|THE\s+[A-Z][A-Z '\.-]*)\s*:\s*(.*)$")
SECTION_PATTERN = re.compile(r"^[A-Z0-9 ,.'&/\-]{4,}$")


def normalize_text(text: str) -> str:
    """Normalize transcript line endings and strip trailing space."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def wrap_qa_blocks_for_ai(text: str) -> str:
    """Wrap contiguous Q/A sections in stable markers before AI correction."""
    lines = normalize_text(text).split("\n")
    output: list[str] = []
    block: list[str] = []

    def flush_block() -> None:
        if not block:
            return
        output.append("[Q_BLOCK]")
        output.extend(block)
        output.append("[/Q_BLOCK]")
        block.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if QA_PATTERN.match(line):
            block.append(line)
            continue

        if block and line and not _is_new_entry(line):
            block.append(line)
            continue

        flush_block()
        output.append(raw_line)

    flush_block()
    return "\n".join(output).strip()


def unwrap_qa_blocks(text: str) -> str:
    """Remove internal AI markers after processing."""
    cleaned = re.sub(r"(?m)^\[/?Q_BLOCK\]\s*$", "", normalize_text(text))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_transcript_text(text: str) -> list[dict[str, str]]:
    """Convert transcript text into deterministic export entries."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in normalize_text(text).split("\n"):
        line = raw_line.strip()
        if not line:
            current = None
            continue

        qa_match = QA_PATTERN.match(line)
        if qa_match:
            current = {"type": qa_match.group(1).upper(), "text": qa_match.group(2).strip()}
            entries.append(current)
            continue

        colloquy_match = COLLOQUY_PATTERN.match(line)
        if colloquy_match:
            current = {
                "type": "COLLOQUY",
                "speaker_label": colloquy_match.group(1).strip().upper(),
                "text": colloquy_match.group(2).strip(),
            }
            entries.append(current)
            continue

        if line.startswith("(") and line.endswith(")"):
            current = {"type": "PAREN", "text": line[1:-1].strip()}
            entries.append(current)
            continue

        if SECTION_PATTERN.fullmatch(line) and len(line.split()) <= 8:
            current = {"type": "SECTION", "text": line}
            entries.append(current)
            continue

        if current is None:
            current = {"type": "PLAIN", "text": line}
            entries.append(current)
            continue

        current["text"] = f"{current['text']} {line}".strip()

    return [entry for entry in entries if entry.get("text") or entry.get("speaker_label")]


def render_entries(entries: list[dict[str, str]]) -> str:
    """Render parsed entries back into a stable preview text format."""
    rendered: list[str] = []

    for entry in entries:
        entry_type = entry.get("type", "PLAIN").upper()
        text = str(entry.get("text", "")).strip()
        if entry_type == "Q":
            rendered.append(f"Q. {text}")
        elif entry_type == "A":
            rendered.append(f"A. {text}")
        elif entry_type == "COLLOQUY":
            rendered.append(f"{entry.get('speaker_label', '').strip()}: {text}".strip())
        elif entry_type == "PAREN":
            rendered.append(f"({text})")
        elif entry_type == "SECTION":
            rendered.append(text.upper())
        else:
            rendered.append(text)

    return "\n\n".join(line for line in rendered if line).strip()


def infer_witness_name(file_path: str | None, text: str) -> str:
    """Infer a witness name from the file name or transcript content."""
    if file_path:
        stem = Path(file_path).stem.replace("_", " ").replace("-", " ").strip()
        if stem:
            return stem.title()

    match = re.search(r"Q\.\s+Please state your full name for the record\.\s+A\.\s+([A-Za-z .'-]+)", text, re.I | re.S)
    if match:
        return match.group(1).strip()

    return "Unknown Witness"


def _is_new_entry(line: str) -> bool:
    return bool(QA_PATTERN.match(line) or COLLOQUY_PATTERN.match(line) or (line.startswith("(") and line.endswith(")")))
