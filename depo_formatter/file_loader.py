from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from docx import Document


SPEAKER_LABEL_PATTERN = re.compile(r"^Speaker\s+(\d):?\s*$", re.IGNORECASE)
ABBREVIATIONS = re.compile(
    r"\b(Dr|Mr|Mrs|Ms|Jr|Sr|vs|No|Vol|Dept|Corp|Inc|Ltd|P\.C|PLLC|St|Ave|Blvd)\.$",
    re.IGNORECASE,
)
ATTORNEY_KEYWORDS = re.compile(
    r"i\s+am\s+\w+.*i\s+represent|my\s+name\s+is\s+\w+.*counsel|"
    r"representing\s+the\s+(plaintiff|defendant)|counsel\s+for\s+the\s+(plaintiff|defendant)",
    re.IGNORECASE,
)
REPORTER_KEYWORDS = re.compile(
    r"raise\s+your\s+right\s+hand|do\s+you\s+solemnly|"
    r"swear\s+or\s+affirm|spell\s+your\s+name|the\s+reporter",
    re.IGNORECASE,
)
VIDEOGRAPHER_KEYWORDS = re.compile(
    r"we\s+are\s+(now\s+)?on\s+(the\s+)?record|"
    r"going\s+off\s+(the\s+)?record|this\s+is\s+the\s+video",
    re.IGNORECASE,
)


@dataclass
class SpeakerMap:
    witness: int | None = None
    lead_attorney: int | None = None
    opposing_attorney: int | None = None
    court_reporter: int | None = None
    videographer: int | None = None
    unassigned: list[int] = field(default_factory=list)


@dataclass
class LoadedTranscript:
    text: str
    source_type: str
    blocks: list[tuple[int, list[str]]] = field(default_factory=list)
    speaker_map: SpeakerMap | None = None


def load_transcript(path: str) -> LoadedTranscript:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return LoadedTranscript(text=load_txt(path), source_type="txt")
    if suffix == ".docx":
        return load_docx_transcript(path)
    if suffix == ".pdf":
        return LoadedTranscript(text=load_pdf(path), source_type="pdf")

    raise ValueError("Unsupported file type. Please select a .txt, .docx, or .pdf file.")


def load_file(path: str) -> str:
    return load_transcript(path).text


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_docx(path: str) -> str:
    return load_docx_transcript(path).text


def load_docx_transcript(path: str) -> LoadedTranscript:
    blocks, speaker_map = parse_deepgram_docx(path)
    if blocks:
        return LoadedTranscript(
            text=render_blocks(blocks),
            source_type="docx",
            blocks=blocks,
            speaker_map=speaker_map,
        )

    document = Document(path)
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return LoadedTranscript(
        text="\n".join(paragraphs).strip(),
        source_type="docx",
        blocks=[],
        speaker_map=speaker_map,
    )


def load_pdf(path: str) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())

    return "\n\n".join(pages).strip()


def detect_speaker_label(paragraph_text: str) -> int | None:
    match = SPEAKER_LABEL_PATTERN.match(paragraph_text.strip())
    if match:
        return int(match.group(1))
    return None


def split_into_paragraphs(text: str) -> list[str]:
    raw_parts = re.split(r"(?<=[.?!])\s+(?=[A-Z])", text.strip())

    paragraphs: list[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if paragraphs and ABBREVIATIONS.search(paragraphs[-1]):
            paragraphs[-1] = f"{paragraphs[-1]} {part}"
        else:
            paragraphs.append(part)

    return paragraphs


def assemble_block(speaker_id: int, fragments: list[str]) -> tuple[int, list[str]]:
    joined = " ".join(fragments)
    joined = re.sub(r" +", " ", joined).strip()

    paragraphs = split_into_paragraphs(joined)
    if not paragraphs:
        paragraphs = [joined] if joined else []

    return speaker_id, paragraphs


def build_speaker_map(blocks: list[tuple[int, list[str]]], scan_limit: int = 30) -> SpeakerMap:
    sample = blocks[:scan_limit]
    block_counts = Counter(speaker_id for speaker_id, _ in sample)

    speaker_text: dict[int, str] = {}
    for speaker_id, paragraphs in sample:
        speaker_text.setdefault(speaker_id, "")
        speaker_text[speaker_id] += " " + " ".join(paragraphs)

    speaker_map = SpeakerMap()
    assigned: set[int] = set()

    for sid, text in speaker_text.items():
        if REPORTER_KEYWORDS.search(text) and speaker_map.court_reporter is None:
            speaker_map.court_reporter = sid
            assigned.add(sid)
        elif VIDEOGRAPHER_KEYWORDS.search(text) and speaker_map.videographer is None:
            speaker_map.videographer = sid
            assigned.add(sid)
        elif ATTORNEY_KEYWORDS.search(text):
            if speaker_map.lead_attorney is None:
                speaker_map.lead_attorney = sid
                assigned.add(sid)
            elif speaker_map.opposing_attorney is None:
                speaker_map.opposing_attorney = sid
                assigned.add(sid)

    remaining = [(sid, count) for sid, count in block_counts.most_common() if sid not in assigned]
    for sid, _count in remaining:
        if speaker_map.witness is None:
            speaker_map.witness = sid
            assigned.add(sid)
        elif speaker_map.lead_attorney is None:
            speaker_map.lead_attorney = sid
            assigned.add(sid)
        elif speaker_map.opposing_attorney is None:
            speaker_map.opposing_attorney = sid
            assigned.add(sid)
        elif speaker_map.videographer is None:
            speaker_map.videographer = sid
            assigned.add(sid)
        else:
            speaker_map.unassigned.append(sid)

    return speaker_map


def parse_deepgram_docx(docx_path: str) -> tuple[list[tuple[int, list[str]]], SpeakerMap]:
    doc = Document(docx_path)

    blocks: list[tuple[int, list[str]]] = []
    current_speaker: int | None = None
    current_fragments: list[str] = []

    for para in doc.paragraphs:
        text = para.text
        speaker_id = detect_speaker_label(text)

        if speaker_id is not None:
            if current_speaker is not None and current_fragments:
                blocks.append(assemble_block(current_speaker, current_fragments))
            current_speaker = speaker_id
            current_fragments = []
        elif current_speaker is not None:
            current_fragments.append(text)

    if current_speaker is not None and current_fragments:
        blocks.append(assemble_block(current_speaker, current_fragments))

    speaker_map = build_speaker_map(blocks, scan_limit=30)
    return blocks, speaker_map


def render_blocks(blocks: list[tuple[int, list[str]]]) -> str:
    rendered_blocks: list[str] = []
    for speaker_id, paragraphs in blocks:
        block_lines = [f"Speaker {speaker_id}:"]
        block_lines.extend(paragraphs)
        rendered_blocks.append("\n".join(line for line in block_lines if line.strip()))
    return "\n\n".join(rendered_blocks).strip()
