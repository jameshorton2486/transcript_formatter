"""
formatter.py — UFM-compliant text formatting rules engine.

FIXES vs. original:
  - WRAP_WIDTH changed from 72 → 65  (UFM §2.5: 6.5" × 10 CPI = 65 chars)
  - CONTINUATION_INDENT changed from 5 spaces → "" (empty)
    UFM §2.10: continuation lines return to LEFT MARGIN, not indented 5 spaces
  - Q/A label detection now handles period, colon, or dash after Q/A
  - Added REPORTER_LABEL normalization (THE COURT REPORTER → THE REPORTER)
  - Added em dash / en dash → double hyphen normalization
  - Added time format normalization (2:12 PM → 2:12 p.m.)
  - Added deterministic normalization for Okay./Mm-hmm, section headers,
    sentence spacing, simple percent/money, and as-read parentheticals
"""

import re
import textwrap


# VERBATIM PRESERVATION: filler word removal is PROHIBITED in legal transcripts.
# This constant is kept only for reference. The remove_filler_words function
# is permanently disabled — it will never remove words regardless of caller arguments.
FILLER_WORDS: tuple = ()
WRAP_WIDTH = 65                             # FIX: was 72, must be 65 (UFM §2.5)
CONTINUATION_INDENT = ""                   # FIX: was " " * 5, must be "" (UFM §2.10)
QA_INDENT = ""                             # Q./A. start at left margin; tabs position them
QA_WIDTH = 56                              # 65 - 9 (tab + label + tab occupies ~9 chars)


# ── Text normalization ────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r'([.?]["\')\]]*) {2,}', r"\1<<DOUBLE_SPACE>>", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.replace("<<DOUBLE_SPACE>>", "  ")
    return cleaned.strip()


def normalize_dashes(text: str) -> str:
    """Replace em dashes and en dashes with double hyphen per UFM §2.8."""
    text = text.replace("\u2014", " -- ")  # em dash —
    text = text.replace("\u2013", " -- ")  # en dash –
    text = re.sub(r"\s*---\s*", " -- ", text)
    return text


def normalize_time_format(text: str) -> str:
    """Normalize time to '2:12 p.m.' format."""
    def _fix(m: re.Match) -> str:
        hour = str(int(m.group(1)))
        period = m.group(3).lower().replace(" ", "")
        if "." not in period:
            period = period[0] + "." + period[1] + "."
        return f"{hour}:{m.group(2)} {period}"

    return re.compile(
        r"\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?|AM|PM|am|pm)\b\.?",
        re.IGNORECASE,
    ).sub(_fix, text)


def normalize_reporter_label(text: str) -> str:
    """THE COURT REPORTER → THE REPORTER (UFM §3.20)."""
    return re.sub(r"\bTHE COURT REPORTER\s*:", "THE REPORTER:", text)


def normalize_universal_corrections(text: str) -> str:
    """Apply deterministic word/label corrections that do not require context."""
    text = re.sub(r"(?<!\w)[Kk]\.(?=\s|$)", "Okay.", text)
    text = re.sub(r"\b(?:Mhmm|Mmhm)\b", "Mm-hmm", text)
    return text


def normalize_as_read_parenthetical(text: str) -> str:
    """Normalize document-reading parentheticals to the legal-house style."""
    text = re.sub(r"\((?:reading|read into the record)\)", "(as read)", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(?:reading|read into the record)\]", "(as read)", text, flags=re.IGNORECASE)
    return text


def normalize_section_headers(text: str) -> str:
    """Normalize examination headers to the required hyphenated forms."""
    replacements = {
        "DIRECT EXAMINATION": "DIRECT EXAMINATION",
        "CROSS EXAMINATION": "CROSS-EXAMINATION",
        "CROSS-EXAMINATION": "CROSS-EXAMINATION",
        "REDIRECT EXAMINATION": "REDIRECT EXAMINATION",
        "RECROSS EXAMINATION": "RECROSS-EXAMINATION",
        "RECROSS-EXAMINATION": "RECROSS-EXAMINATION",
    }
    normalized_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        upper = stripped.upper()
        if upper in replacements:
            normalized_lines.append(replacements[upper])
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


def normalize_percent_and_money(text: str) -> str:
    """Apply simple numeric formatting that is safe without semantic inference."""
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*%", r"\1 percent", text)
    text = re.sub(r"\$(\d{1,3}(?:,\d{3})*|\d+)\.00\b", r"$\1", text)
    return text


def normalize_sentence_spacing(text: str) -> str:
    """Apply two spaces after sentence-ending period/question mark where safe."""
    return re.sub(
        r"(?<!\.)(([.?])(?:[\"')\]]*)?)\s+(?=[A-Z(\[\"'])",
        lambda m: f"{m.group(1)}  ",
        text,
    )


def remove_filler_words(text: str) -> str:
    """
    PERMANENTLY DISABLED — verbatim preservation rule prohibits filler word removal.
    Kept for API compatibility only. Returns text unchanged.
    """
    return text


# ── Q/A formatting ────────────────────────────────────────────────────────────

def detect_existing_label(segment: str) -> tuple[str, str] | None:
    """Detect Q. or A. label at start of segment. Returns (label, content) or None."""
    m = re.match(r"^\s*([QqAa])[\.\:\-]\s*(.+?)\s*$", segment, re.DOTALL)
    if not m:
        return None
    label = "Q." if m.group(1).upper() == "Q" else "A."
    return label, m.group(2)


def detect_speaker_label(segment: str) -> tuple[str, str] | None:
    """
    Detect speaker labels beyond Q. and A.:
      THE REPORTER:, THE INTERPRETER:, MR. SMITH:, MS. JONES:, etc.
    Returns (label, content) or None.
    """
    m = re.match(
        r"^\s*((?:THE\s+\w+|MR\.|MS\.|MRS\.|DR\.)\s*[\w\s]*?):\s*(.+?)$",
        segment.strip(),
        re.DOTALL,
    )
    if not m:
        return None
    return m.group(1).strip().upper(), m.group(2).strip()


def apply_qa_format(text: str) -> str:
    """
    Format transcript with Q./A. labels.
    Continuation lines return to left margin (CONTINUATION_INDENT = "").
    """
    normalized = clean_text(text)
    if not normalized:
        return ""

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not any(detect_existing_label(line) for line in lines):
        return wrap_text(normalized)

    formatted_sections: list[str] = []

    for segment in lines:
        detected = detect_existing_label(segment)
        if detected:
            label, content = detected
            # FIX: initial_indent is just the label + space; subsequent is empty (left margin)
            wrapped = wrap_text(content, initial_indent=f"{label} ", subsequent_indent=CONTINUATION_INDENT)
            formatted_sections.append(wrapped)
            continue

        speaker_detected = detect_speaker_label(segment)
        if speaker_detected:
            label, content = speaker_detected
            wrapped = wrap_text(content, initial_indent=f"{label}: ", subsequent_indent=CONTINUATION_INDENT)
            formatted_sections.append(wrapped)
        else:
            formatted_sections.append(wrap_text(segment))

    return "\n\n".join(s for s in formatted_sections if s.strip())


def wrap_text(
    text: str,
    width: int = WRAP_WIDTH,
    initial_indent: str = "",
    subsequent_indent: str = CONTINUATION_INDENT,
) -> str:
    stripped = clean_text(text)
    if not stripped:
        return ""

    wrapped_lines: list[str] = []
    for paragraph in stripped.split("\n"):
        if not paragraph.strip():
            continue
        wrapped_lines.append(
            textwrap.fill(
                paragraph.strip(),
                width=width,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )

    return "\n".join(wrapped_lines)


# ── Main entry point ──────────────────────────────────────────────────────────

def format_transcript(
    text: str,
    use_qa_format: bool = True,
    remove_fillers: bool = False,
) -> str:
    formatted = clean_text(text)
    formatted = normalize_dashes(formatted)
    formatted = normalize_universal_corrections(formatted)
    formatted = normalize_time_format(formatted)
    formatted = normalize_reporter_label(formatted)
    formatted = normalize_as_read_parenthetical(formatted)
    formatted = normalize_section_headers(formatted)
    formatted = normalize_percent_and_money(formatted)
    formatted = normalize_sentence_spacing(formatted)

    if remove_fillers:
        formatted = remove_filler_words(formatted)

    if use_qa_format:
        formatted = apply_qa_format(formatted)
    else:
        formatted = wrap_text(formatted)

    return clean_text(formatted)
