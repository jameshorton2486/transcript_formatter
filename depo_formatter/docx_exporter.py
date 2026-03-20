from pathlib import Path

from docx import Document
from docx.shared import Pt


def export_to_docx(text: str, output_path: str) -> str:
    if not text.strip():
        raise ValueError("There is no transcript content to export.")

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Courier New"
    style.font.size = Pt(12)

    for line in text.splitlines():
        paragraph = document.add_paragraph()
        run = paragraph.add_run(line.rstrip())
        run.font.name = "Courier New"
        run.font.size = Pt(12)

    destination = Path(output_path)
    if destination.suffix.lower() != ".docx":
        destination = destination.with_suffix(".docx")

    document.save(destination)
    return str(destination)
