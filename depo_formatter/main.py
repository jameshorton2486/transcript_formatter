"""
NEW main.py — Depo Transcript Formatter (AI-Assisted)
Complete UI redesign for Depo-Pro / SA Legal Solutions

Design decisions:
  - Two-panel layout: left sidebar controls, right transcript preview
  - Progress bar for AI operations (no more frozen UI)
  - Threading for all AI calls
  - No hardcoded PII defaults
  - Completion status badge (draft vs. final export)
  - Dedicated settings panel for header/footer/format preferences
  - Clean professional legal tool aesthetic (dark, high contrast, monospace preview)
"""

import json
import os
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from dotenv import load_dotenv

from app_logging import get_logger
from ai_tools import (
    extract_proper_nouns_from_pdf,
    run_ai_review_tool,
    run_ai_tool,
    test_anthropic_connection,
)
from docx_exporter import export_to_docx
from file_loader import load_transcript
from formatter import format_transcript

APP_DIR = Path(__file__).resolve().parent
DOTENV_PATH = APP_DIR / ".env"
SESSION_PATH = APP_DIR / "session_state.json"
load_dotenv(dotenv_path=DOTENV_PATH)
LOGGER = get_logger(__name__)

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_SURFACE   = "#1a1d23"
BG_PANEL     = "#22262e"
BG_INPUT     = "#2a2f3a"
ACCENT_BLUE  = "#3b82f6"
ACCENT_GREEN = "#22c55e"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED   = "#ef4444"
TEXT_PRIMARY = "#f1f5f9"
TEXT_MUTED   = "#64748b"
BORDER       = "#2e3340"
FONT_MONO    = ("Courier New", 13)
FONT_LABEL   = ("Segoe UI", 12)
FONT_SMALL   = ("Segoe UI", 10)


class Badge(ctk.CTkFrame):
    """Small status badge: Draft / Final / Processing."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=BG_PANEL, corner_radius=6, **kwargs)
        self._dot = ctk.CTkLabel(self, text="●", font=("Segoe UI", 10), width=16)
        self._dot.grid(row=0, column=0, padx=(8, 2), pady=4)
        self._label = ctk.CTkLabel(self, text="Draft", font=FONT_SMALL, text_color=TEXT_MUTED)
        self._label.grid(row=0, column=1, padx=(0, 10), pady=4)
        self.set_draft()

    def set_draft(self):
        self._dot.configure(text_color=ACCENT_AMBER)
        self._label.configure(text="Draft Mode")

    def set_final(self):
        self._dot.configure(text_color=ACCENT_GREEN)
        self._label.configure(text="Ready for Final Export")

    def set_processing(self):
        self._dot.configure(text_color=ACCENT_BLUE)
        self._label.configure(text="Processing…")


class SectionHeader(ctk.CTkLabel):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent,
            text=text.upper(),
            font=("Segoe UI", 9),
            text_color=TEXT_MUTED,
            anchor="w",
            **kwargs,
        )


class DepoTranscriptFormatterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Depo Transcript Formatter")
        self.geometry("1280x820")
        self.minsize(960, 640)
        self.configure(fg_color=BG_SURFACE)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.loaded_file_path: str | None = None
        self.status_var = tk.StringVar(value="Load a transcript file to begin.")
        self.dash_style_var = tk.StringVar(value="double-hyphen")
        self.history: list[dict] = []
        self._busy_running = False

        self._build_layout()
        self.restore_session()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)   # left sidebar
        self.grid_columnconfigure(1, weight=1)   # right preview
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_preview_panel()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, width=300)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(99, weight=1)  # push bottom items down

        row = 0

        # ── App title ─────────────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        title_frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            title_frame,
            text="DEPO FORMATTER",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")
        row += 1

        ctk.CTkLabel(
            sidebar,
            text="SA Legal Solutions · AI-Assisted",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 16))
        row += 1

        # ── File section ──────────────────────────────────────────────────────
        ctk.CTkFrame(sidebar, fg_color=BORDER, height=1).grid(
            row=row, column=0, sticky="ew", padx=16, pady=(0, 12)
        )
        row += 1

        SectionHeader(sidebar, "File").grid(row=row, column=0, sticky="ew", padx=20)
        row += 1

        self.file_label = ctk.CTkLabel(
            sidebar,
            text="No file loaded",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=260,
        )
        self.file_label.grid(row=row, column=0, sticky="ew", padx=20, pady=(4, 8))
        row += 1

        ctk.CTkButton(
            sidebar,
            text="Upload Transcript",
            command=self.upload_file,
            height=36,
            font=FONT_LABEL,
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 12))
        row += 1

        # ── Actions section ───────────────────────────────────────────────────
        ctk.CTkFrame(sidebar, fg_color=BORDER, height=1).grid(
            row=row, column=0, sticky="ew", padx=16, pady=(0, 12)
        )
        row += 1

        SectionHeader(sidebar, "Actions").grid(row=row, column=0, sticky="ew", padx=20)
        row += 1

        # Format button
        ctk.CTkButton(
            sidebar,
            text="▶  Format (Rules Engine)",
            command=self.run_rules_formatter,
            height=36,
            font=FONT_LABEL,
            fg_color=BG_INPUT,
            hover_color="#3a404d",
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(6, 4))
        row += 1

        # AI Legal Correction button
        ctk.CTkButton(
            sidebar,
            text="✦  AI Legal Correction",
            command=self.run_legal_correction,
            height=36,
            font=FONT_LABEL,
            fg_color=BG_INPUT,
            hover_color="#3a404d",
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=4)
        row += 1

        # Open in Word (Windows only)
        ctk.CTkButton(
            sidebar,
            text="📄  Word Track Changes",
            command=self.open_word_track_changes_review,
            height=36,
            font=FONT_LABEL,
            fg_color=BG_INPUT,
            hover_color="#3a404d",
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=4)
        row += 1

        # Undo
        ctk.CTkButton(
            sidebar,
            text="↩  Undo Last Action",
            command=self.reset_last_action,
            height=32,
            font=FONT_SMALL,
            fg_color="transparent",
            hover_color="#2a2f3a",
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=BORDER,
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(8, 4))
        row += 1

        # ── AI Config section ─────────────────────────────────────────────────
        ctk.CTkFrame(sidebar, fg_color=BORDER, height=1).grid(
            row=row, column=0, sticky="ew", padx=16, pady=(12, 12)
        )
        row += 1

        SectionHeader(sidebar, "AI Configuration").grid(row=row, column=0, sticky="ew", padx=20)
        row += 1

        nouns_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        nouns_header.grid(row=row, column=0, sticky="ew", padx=20, pady=(6, 2))
        nouns_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            nouns_header,
            text="Proper Nouns",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            nouns_header,
            text="+ Import PDF",
            command=self.import_proper_nouns_from_pdf,
            height=20,
            width=84,
            font=("Segoe UI", 9),
            fg_color=ACCENT_BLUE,
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=4,
        ).grid(row=0, column=1, sticky="e")
        row += 1

        self.proper_nouns_text = ctk.CTkTextbox(
            sidebar, height=110, wrap="word", font=FONT_SMALL,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
        )
        self.proper_nouns_text.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 8))
        # NOTE: starts EMPTY — no hardcoded real names
        row += 1

        ctk.CTkLabel(sidebar, text="Dash Style", font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w").grid(
            row=row, column=0, sticky="ew", padx=20, pady=(0, 2)
        )
        row += 1

        ctk.CTkOptionMenu(
            sidebar,
            values=["double-hyphen", "em-dash"],
            variable=self.dash_style_var,
            height=32,
            font=FONT_SMALL,
            fg_color=BG_INPUT,
            button_color=BG_INPUT,
            button_hover_color="#3a404d",
            dropdown_fg_color=BG_INPUT,
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 8))
        row += 1

        # ── API key status ─────────────────────────────────────────────────────
        ctk.CTkFrame(sidebar, fg_color=BORDER, height=1).grid(
            row=row, column=0, sticky="ew", padx=16, pady=(4, 8)
        )
        row += 1

        self._api_indicator = ctk.CTkLabel(
            sidebar,
            text=self._get_api_status_text(),
            font=FONT_SMALL,
            text_color=ACCENT_GREEN if self._has_api_key() else ACCENT_RED,
            anchor="w",
        )
        self._api_indicator.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 4))
        row += 1

        ctk.CTkButton(
            sidebar,
            text="Test API Connection",
            command=self.run_connection_test,
            height=28,
            font=FONT_SMALL,
            fg_color="transparent",
            hover_color="#2a2f3a",
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=BORDER,
        ).grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 16))
        row += 1

        # ── Bottom: clear + version ────────────────────────────────────────────
        row = 99  # pushed to bottom via rowconfigure weight

        ctk.CTkButton(
            sidebar,
            text="Clear Session",
            command=self.clear_session,
            height=28,
            font=FONT_SMALL,
            fg_color="transparent",
            hover_color=BG_INPUT,
            text_color=TEXT_MUTED,
        ).grid(row=row, column=0, sticky="sew", padx=20, pady=(4, 20))

    def _build_preview_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        # ── Top bar ───────────────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(panel, fg_color=BG_PANEL, corner_radius=0, height=52)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.grid_propagate(False)
        top_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="Transcript Preview",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=14)

        self._badge = Badge(top_bar)
        self._badge.grid(row=0, column=1, sticky="e", padx=20)

        # ── Preview area ──────────────────────────────────────────────────────
        preview_frame = ctk.CTkFrame(panel, fg_color=BG_SURFACE, corner_radius=0)
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(16, 0))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)

        self.preview_text = ctk.CTkTextbox(
            preview_frame,
            wrap="word",
            font=FONT_MONO,
            fg_color=BG_INPUT,
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")

        # ── Progress bar (hidden by default) ─────────────────────────────────
        self._progress = ctk.CTkProgressBar(panel, height=3, fg_color=BG_PANEL, progress_color=ACCENT_BLUE)
        self._progress.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self._progress.set(0)
        self._progress.grid_remove()  # hidden until AI call starts

        # ── Bottom status + export bar ────────────────────────────────────────
        bottom_bar = ctk.CTkFrame(panel, fg_color=BG_PANEL, corner_radius=0, height=56)
        bottom_bar.grid(row=3, column=0, sticky="ew")
        bottom_bar.grid_propagate(False)
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            bottom_bar,
            textvariable=self.status_var,
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=20, pady=16)

        ctk.CTkButton(
            bottom_bar,
            text="Export to Word (.docx)",
            command=self.export_docx,
            height=36,
            width=200,
            font=FONT_LABEL,
            fg_color=ACCENT_GREEN,
            hover_color="#16a34a",
            text_color="#0a1a0a",
        ).grid(row=0, column=1, sticky="e", padx=20, pady=10)

    # ── Background work + progress helpers ───────────────────────────────────

    def _start_busy(self, label: str) -> None:
        """Show progress state for format/AI/background operations."""
        self._busy_running = True
        self._badge.set_processing()
        self.status_var.set(f"Running {label}…")
        self._progress.grid()
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self.update_idletasks()

    def _stop_busy(self) -> None:
        """Hide progress state after format/AI/background operations."""
        self._busy_running = False
        self._progress.stop()
        self._progress.grid_remove()
        self._badge.set_draft()

    def _run_in_thread(self, fn, *args, on_success=None, on_error=None):
        """Run fn(*args) in a background thread, call on_success/on_error on main thread."""
        def worker():
            try:
                result = fn(*args)
                if on_success:
                    self.after(0, lambda: on_success(result))
            except Exception as exc:
                LOGGER.exception("Background AI call failed")
                if on_error:
                    self.after(0, lambda: on_error(exc))
            finally:
                self.after(0, self._stop_busy)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ── File loading ──────────────────────────────────────────────────────────

    def upload_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select transcript file",
            filetypes=(
                ("Supported files", "*.txt *.json *.docx *.pdf"),
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("Word documents", "*.docx"),
                ("PDF files", "*.pdf"),
            ),
        )
        if not file_path:
            return

        try:
            loaded = load_transcript(file_path)
        except Exception as exc:
            self.show_error("Load Error", str(exc))
            return

        transcript = loaded.text
        if not transcript.strip():
            self.show_warning("Empty File", "The selected file did not contain extractable text.")
            return

        self.push_history()
        self.loaded_file_path = file_path
        self.file_label.configure(text=Path(file_path).name, text_color=TEXT_PRIMARY)
        self.set_preview_text(transcript)
        self.status_var.set(self._build_loaded_status(Path(file_path).name, loaded))
        self.save_session()

    # ── Format ────────────────────────────────────────────────────────────────

    def run_rules_formatter(self) -> None:
        if self._busy_running:
            return

        text = self.get_preview_text()
        if not text.strip():
            self.show_warning("No Transcript", "Load a transcript before formatting.")
            return

        self._start_busy("Format (Rules Engine)")

        def on_success(formatted: str):
            self.push_history()
            self.set_preview_text(formatted)
            self.status_var.set("Deterministic formatting applied.")
            self.save_session()

        def on_error(exc):
            self.status_var.set("Formatting failed.")
            self.show_error("Formatting Error", str(exc))

        self._run_in_thread(
            format_transcript,
            text,
            on_success=on_success,
            on_error=on_error,
        )

    # ── AI Legal Correction ───────────────────────────────────────────────────

    def run_legal_correction(self) -> None:
        if self._busy_running:
            return

        selected = self.get_selected_text()
        source   = selected if selected.strip() else self.get_preview_text()

        if not source.strip():
            self.show_warning("No Transcript", "Load a transcript before using AI.")
            return

        self._start_busy("AI Legal Correction")

        def on_success(result):
            self.show_ai_result_dialog(
                "AI Legal Correction",
                result,
                replace_selection=bool(selected.strip()),
            )
            self.status_var.set("AI correction result ready for review.")

        def on_error(exc):
            self.status_var.set("AI request failed.")
            self.show_error("AI Error", str(exc))

        self._run_in_thread(
            run_ai_tool,
            source,
            self.get_proper_nouns(),
            self.dash_style_var.get(),
            on_success=on_success,
            on_error=on_error,
        )

    # ── Word Track Changes ────────────────────────────────────────────────────

    def open_word_track_changes_review(self) -> None:
        try:
            from word_review import derive_review_output_path, open_word_with_track_changes
        except ImportError:
            self.show_error(
                "Windows Only",
                "Track Changes review requires Microsoft Word and pywin32.\n"
                "This feature is only available on Windows.",
            )
            return

        if self._busy_running:
            return

        text = self.get_preview_text()
        if not text.strip():
            self.show_warning("No Transcript", "Load a transcript before starting Word review.")
            return

        self._start_busy("Word Track Changes")

        def on_success(result):
            corrected_text, output_path = result
            try:
                final = open_word_with_track_changes(text, corrected_text, output_path)
                self.status_var.set(f"Word review ready: {Path(final).name}")
                self.show_info("Word Review Ready", f"Opened Word with Track Changes.\n\n{final}")
            except Exception as exc:
                self.show_error("Word Error", str(exc))

        def on_error(exc):
            self.status_var.set("Word review failed.")
            self.show_error("Word Review Error", str(exc))

        def run_word():
            corrected = run_ai_review_tool(
                text,
                proper_nouns=self.get_proper_nouns(),
                dash_style=self.dash_style_var.get(),
            )
            output_path = derive_review_output_path(self.loaded_file_path)
            return corrected, output_path

        self._run_in_thread(run_word, on_success=on_success, on_error=on_error)

    # ── AI result dialog ──────────────────────────────────────────────────────

    def show_ai_result_dialog(self, title: str, result_text: str, replace_selection: bool) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("940x680")
        dialog.configure(fg_color=BG_SURFACE)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Review the AI output before applying. You can edit it here.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))

        result_box = ctk.CTkTextbox(
            dialog, wrap="word", font=FONT_MONO,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
        )
        result_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=8)
        result_box.insert("1.0", result_text)

        btn_row = ctk.CTkFrame(dialog, fg_color=BG_PANEL, corner_radius=0)
        btn_row.grid(row=2, column=0, sticky="ew")
        btn_row.grid_columnconfigure(1, weight=1)

        def apply_result():
            reviewed = result_box.get("1.0", "end").strip()
            self.push_history()
            if replace_selection:
                self.replace_selected_text(reviewed)
            else:
                self.set_preview_text(reviewed)
            self.status_var.set(f"{title} applied.")
            self.save_session()
            dialog.destroy()

        ctk.CTkButton(
            btn_row, text="Apply Result", command=apply_result,
            height=36, fg_color=ACCENT_GREEN, hover_color="#16a34a", text_color="#0a1a0a",
            font=FONT_LABEL,
        ).grid(row=0, column=0, padx=(20, 8), pady=16)

        ctk.CTkButton(
            btn_row, text="Discard", command=dialog.destroy,
            height=36, fg_color="transparent", hover_color=BG_INPUT,
            text_color=TEXT_MUTED, border_width=1, border_color=BORDER, font=FONT_SMALL,
        ).grid(row=0, column=2, padx=(8, 20), pady=16)

    def import_proper_nouns_from_pdf(self) -> None:
        """Open a PDF, extract proper nouns via AI, merge into the nouns field."""
        if self._busy_running:
            self.show_warning("AI Busy", "Wait for the current AI operation to finish.")
            return

        file_path = filedialog.askopenfilename(
            title="Select legal document PDF",
            filetypes=(
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ),
        )
        if not file_path:
            return

        try:
            import pdfplumber

            pages: list[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text.strip())
            pdf_text = "\n\n".join(pages)
        except Exception as exc:
            self.show_error("PDF Error", f"Could not read PDF:\n{exc}")
            return

        if not pdf_text.strip():
            self.show_warning(
                "Empty PDF",
                "No extractable text found in this PDF.\n"
                "Scanned/image PDFs are not supported.",
            )
            return

        self._start_busy("Extracting proper nouns from PDF")
        LOGGER.info("PDF noun import | file=%s chars=%s", Path(file_path).name, len(pdf_text))

        def on_success(new_nouns: list[str]) -> None:
            existing = self.get_proper_nouns()
            existing_lower = {noun.lower() for noun in existing}
            added = [noun for noun in new_nouns if noun.lower() not in existing_lower]
            merged = existing + added

            self.proper_nouns_text.delete("1.0", "end")
            self.proper_nouns_text.insert("1.0", "\n".join(merged))
            self.save_session()

            msg = (
                f"Extracted {len(new_nouns)} proper noun(s) from {Path(file_path).name}.\n"
                f"{len(added)} new, {len(new_nouns) - len(added)} already present."
            )
            self.status_var.set(msg)
            LOGGER.info("PDF noun import complete | new=%s existing=%s", len(added), len(existing))
            self.show_info("Import Complete", msg)

        def on_error(exc: Exception) -> None:
            self.status_var.set("PDF noun import failed.")
            self.show_error("Import Error", str(exc))

        self._run_in_thread(
            extract_proper_nouns_from_pdf,
            pdf_text,
            on_success=on_success,
            on_error=on_error,
        )

    # ── Connection test ───────────────────────────────────────────────────────

    def run_connection_test(self) -> None:
        if self._busy_running:
            return
        self._start_busy("API Connection Test")

        def on_success(result):
            ok    = result["ok"] == "true"
            model = result.get("model", "unknown")
            code  = result["status_code"]
            self.status_var.set(
                f"API {'connected' if ok else 'failed'} — {model} (status {code})"
            )
            self._api_indicator.configure(
                text=self._get_api_status_text(),
                text_color=ACCENT_GREEN if ok else ACCENT_RED,
            )
            if ok:
                self.show_info("Connected", f"Model: {model}\nStatus: {code}")
            else:
                self.show_error("Failed", f"Status: {code}\n{result.get('body', '')}")

        def on_error(exc):
            self.status_var.set("API connection test failed.")
            self.show_error("Connection Error", str(exc))

        self._run_in_thread(test_anthropic_connection, on_success=on_success, on_error=on_error)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_docx(self) -> None:
        content = self.get_preview_text()
        if not content.strip():
            self.show_warning("Nothing to Export", "No transcript content to export.")
            return

        initial = "formatted_transcript.docx"
        if self.loaded_file_path:
            initial = f"{Path(self.loaded_file_path).stem}_formatted.docx"

        output_path = filedialog.asksaveasfilename(
            title="Save DOCX",
            defaultextension=".docx",
            initialfile=initial,
            filetypes=(("Word Document", "*.docx"),),
        )
        if not output_path:
            return

        try:
            final_path = export_to_docx(content, output_path)
        except Exception as exc:
            self.show_error("Export Error", str(exc))
            return

        self.status_var.set(f"Exported: {Path(final_path).name}")
        self._badge.set_final()
        self.show_info("Exported", f"Saved to:\n{final_path}")

    # ── Session ───────────────────────────────────────────────────────────────

    def reset_last_action(self) -> None:
        if not self.history:
            self.show_info("Nothing to Undo", "No previous action to undo.")
            return
        prev = self.history.pop()
        self.loaded_file_path = prev["loaded_file_path"]
        self.file_label.configure(text=prev["file_label"] or "No file loaded")
        self.set_preview_text(prev["preview_text"] or "")
        self.status_var.set("Undone.")
        self.save_session()

    def clear_session(self) -> None:
        if self.get_preview_text().strip():
            if not messagebox.askyesno("Clear Session", "Clear the current transcript and session?"):
                return
        self.loaded_file_path = None
        self.history.clear()
        self.file_label.configure(text="No file loaded", text_color=TEXT_MUTED)
        self.set_preview_text("")
        self._badge.set_draft()
        self.status_var.set("Session cleared.")
        self.save_session()

    def save_session(self) -> None:
        try:
            SESSION_PATH.write_text(
                json.dumps({
                    "loaded_file_path": self.loaded_file_path,
                    "preview_text":     self.get_preview_text(),
                    "file_label":       self.file_label.cget("text"),
                    "proper_nouns":     self.get_proper_nouns(),
                    "dash_style":       self.dash_style_var.get(),
                    "history":          self.history,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            LOGGER.exception("Failed to save session")

    def restore_session(self) -> None:
        if not SESSION_PATH.exists():
            return
        try:
            data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            self.loaded_file_path = data.get("loaded_file_path")
            label = data.get("file_label") or "No file loaded"
            self.file_label.configure(text=label, text_color=TEXT_PRIMARY if data.get("loaded_file_path") else TEXT_MUTED)
            self.set_preview_text(data.get("preview_text") or "")
            self.history = data.get("history") or []
            nouns = data.get("proper_nouns") or []
            if nouns:
                self.proper_nouns_text.delete("1.0", "end")
                self.proper_nouns_text.insert("1.0", "\n".join(nouns))
            ds = data.get("dash_style")
            if ds in {"double-hyphen", "em-dash"}:
                self.dash_style_var.set(ds)
            if self.get_preview_text():
                self.status_var.set("Previous session restored.")
        except Exception:
            LOGGER.exception("Failed to restore session")

    def on_close(self) -> None:
        self.save_session()
        self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_preview_text(self) -> str:
        return self.preview_text.get("1.0", "end").strip()

    def set_preview_text(self, text: str) -> None:
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)

    def get_selected_text(self) -> str:
        try:
            return self.preview_text.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    def replace_selected_text(self, new_text: str) -> None:
        try:
            self.preview_text.delete("sel.first", "sel.last")
            self.preview_text.insert("insert", new_text)
        except tk.TclError:
            self.set_preview_text(new_text)

    def push_history(self) -> None:
        self.history.append({
            "loaded_file_path": self.loaded_file_path,
            "file_label":       self.file_label.cget("text"),
            "preview_text":     self.get_preview_text(),
        })

    def get_proper_nouns(self) -> list[str]:
        raw = self.proper_nouns_text.get("1.0", "end").strip()
        return [ln.strip() for ln in raw.splitlines() if ln.strip()]

    def _has_api_key(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())

    def _get_api_status_text(self) -> str:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return "⚠ API key not set"
        return f"✓ API key loaded"

    def _build_loaded_status(self, file_name: str, loaded) -> str:
        if getattr(loaded, "source_type", "") == "json":
            speaker_count = len({speaker_id for speaker_id, _ in getattr(loaded, "blocks", [])})
            if speaker_count:
                return (
                    f"Loaded: {file_name} | {speaker_count} speaker(s) detected | "
                    "Run 'AI Legal Correction' to resolve speaker labels."
                )
        return f"Loaded: {file_name}"

    def show_error(self, title: str, message: str) -> None:
        LOGGER.error("%s: %s", title, message)
        messagebox.showerror(title, message, parent=self)

    def show_warning(self, title: str, message: str) -> None:
        LOGGER.warning("%s: %s", title, message)
        messagebox.showwarning(title, message, parent=self)

    def show_info(self, title: str, message: str) -> None:
        LOGGER.info("%s: %s", title, message)
        messagebox.showinfo(title, message, parent=self)


if __name__ == "__main__":
    app = DepoTranscriptFormatterApp()
    app.mainloop()
