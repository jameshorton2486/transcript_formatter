"""Build a final DOCX transcript from multiple rendered UFM templates."""

from __future__ import annotations

import shutil
import uuid
from copy import deepcopy
from pathlib import Path

from docx import Document

from ufm_engine.context_builder import ContextBuilder
from ufm_engine.template_registry import get_template_path
from ufm_engine.template_renderer import TemplateRenderer
from ufm_engine.template_selector import TemplateSelector


class DocumentBuilder:
    """Render selected templates and merge them into one DOCX output."""

    def build_document(self, job_data: dict, output_path: str) -> None:
        """Build a final transcript document from template-driven sections.

        Args:
            job_data: Raw job information used to build template context and
                select applicable templates.
            output_path: Final DOCX path for the assembled transcript.

        Raises:
            FileNotFoundError: If a required template file is missing.
            RuntimeError: If rendering, merging, or saving the document fails.
            ValueError: If upstream context or selection validation fails.
        """
        output_file = Path(output_path)
        temp_dir = Path("temp_render") / uuid.uuid4().hex
        rendered_files: list[Path] = []

        try:
            context = ContextBuilder().build_context(job_data)
            template_names = TemplateSelector().select_templates(job_data)
            print(f"Templates selected: {template_names}")

            temp_dir.mkdir(parents=True, exist_ok=True)
            renderer = TemplateRenderer()

            for template_name in template_names:
                template_path = Path(get_template_path(template_name))
                if not template_path.is_file():
                    raise FileNotFoundError(f"Template file not found: {template_path}")

                temp_file = temp_dir / f"{template_name}_{uuid.uuid4().hex}.docx"
                print(f"Rendering {template_name}...")
                renderer.render_template(
                    template_path=str(template_path),
                    context=context,
                    output_path=str(temp_file),
                )
                print(f"Rendered: {temp_file}")
                rendered_files.append(temp_file)

            print("Merging documents...")
            merged_document = Document()
            self._clear_document_body(merged_document)

            for index, rendered_file in enumerate(rendered_files):
                sub_document = Document(str(rendered_file))
                self._append_document(merged_document, sub_document)
                if index < len(rendered_files) - 1:
                    merged_document.add_page_break()

            output_file.parent.mkdir(parents=True, exist_ok=True)
            merged_document.save(str(output_file))
            print(f"Output saved: {output_file}")
        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Document build failed: {exc}") from exc
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _clear_document_body(document: Document) -> None:
        """Remove the default empty paragraph from a new Document."""
        body = document.element.body
        for element in list(body):
            body.remove(element)

    @staticmethod
    def _append_document(target: Document, source: Document) -> None:
        """Append the body elements from one document into another."""
        for element in list(source.element.body):
            # Section properties are handled by the target document.
            if element.tag.endswith("sectPr"):
                continue
            target.element.body.append(deepcopy(element))
