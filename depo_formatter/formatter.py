import re
import textwrap


FILLER_WORDS = ("um", "uh", "you know", "like")
WRAP_WIDTH = 72
CONTINUATION_INDENT = " " * 5


def clean_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def remove_filler_words(text: str) -> str:
    cleaned = text
    for filler in FILLER_WORDS:
        pattern = re.compile(rf"\b{re.escape(filler)}\b", re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)

    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\s+\?", "?", cleaned)
    cleaned = re.sub(r"\s+!", "!", cleaned)
    return clean_text(cleaned)


def apply_qa_format(text: str) -> str:
    normalized = clean_text(text)
    if not normalized:
        return ""

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not any(detect_existing_label(line) for line in lines):
        return wrap_text(normalized, initial_indent="", subsequent_indent=CONTINUATION_INDENT)

    formatted_sections = []

    for segment in lines:
        detected = detect_existing_label(segment)
        if detected:
            label, content = detected
            wrapped = wrap_text(
                content,
                initial_indent=f"{label} ",
                subsequent_indent=CONTINUATION_INDENT,
            )
            formatted_sections.append(wrapped)
            continue

        wrapped = wrap_text(segment.strip(), initial_indent="", subsequent_indent=CONTINUATION_INDENT)
        formatted_sections.append(wrapped)

    return "\n\n".join(section for section in formatted_sections if section.strip())


def wrap_text(
    text: str,
    width: int = WRAP_WIDTH,
    initial_indent: str = "",
    subsequent_indent: str = CONTINUATION_INDENT,
) -> str:
    stripped = clean_text(text)
    if not stripped:
        return ""

    wrapped_lines = []
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


def format_transcript(
    text: str,
    use_qa_format: bool = True,
    remove_fillers: bool = False,
) -> str:
    formatted = clean_text(text)

    if remove_fillers:
        formatted = remove_filler_words(formatted)

    if use_qa_format:
        formatted = apply_qa_format(formatted)
    else:
        formatted = wrap_text(formatted, initial_indent="", subsequent_indent=CONTINUATION_INDENT)

    return clean_text(formatted)


def detect_existing_label(segment: str) -> tuple[str, str] | None:
    match = re.match(r"^\s*([QqAa])[\.\:\-]\s*(.+?)\s*$", segment)
    if not match:
        return None

    label = "Q." if match.group(1).upper() == "Q" else "A."
    return label, match.group(2)
