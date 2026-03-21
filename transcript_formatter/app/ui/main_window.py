"""Structured GUI for the legal transcript system."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from depo_formatter.app_logging import get_logger
from transcript_formatter.app.controllers.workflow_controller import WorkflowController

LOGGER = get_logger(__name__)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class LegalTranscriptSystemApp(ctk.CTk):
    """Desktop workflow for AI correction, UFM formatting, and export."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = WorkflowController()

        self.title("Legal Transcript System")
        self.geometry("1180x860")
        self.minsize(980, 760)

        self.file_var = tk.StringVar(value="No transcript loaded")
        self.status_var = tk.StringVar(value="Upload a transcript to begin.")
        self.ai_status_var = tk.StringVar(value="AI Not Run")
        self.format_status_var = tk.StringVar(value="Formatting Not Applied")
        self.finalization_status_var = tk.StringVar(value="Finalization Not Applied")
        self.dash_style_var = tk.StringVar(value="double-hyphen")
        self.show_format_box_var = tk.BooleanVar(value=True)
        self.show_line_numbers_var = tk.BooleanVar(value=True)
        self.show_header_var = tk.BooleanVar(value=True)
        self.show_footer_var = tk.BooleanVar(value=True)

        self._build_layout()
        self._refresh_buttons()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        header = ctk.CTkFrame(self, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(header, text="Upload File", command=self.upload_file, width=150).grid(
            row=0, column=0, padx=14, pady=14
        )
        ctk.CTkLabel(header, text="File:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(4, 0), pady=14
        )
        ctk.CTkLabel(header, textvariable=self.file_var, anchor="w").grid(
            row=0, column=2, sticky="ew", padx=(8, 14), pady=14
        )

        ai_frame = ctk.CTkFrame(self, corner_radius=12)
        ai_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=10)
        ai_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(ai_frame, text="STEP 1  AI CORRECTION", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 8)
        )
        ctk.CTkButton(ai_frame, text="Run Legal Correction", command=self.run_ai_correction, width=180).grid(
            row=1, column=0, sticky="w", padx=14, pady=(0, 14)
        )
        ctk.CTkLabel(ai_frame, text="Proper Nouns", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, sticky="w", padx=14, pady=(14, 4)
        )
        self.proper_nouns_text = ctk.CTkTextbox(ai_frame, height=90)
        self.proper_nouns_text.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 14))
        ctk.CTkLabel(ai_frame, text="Dash Style").grid(row=0, column=2, sticky="w", padx=14, pady=(14, 4))
        ctk.CTkOptionMenu(
            ai_frame,
            values=["double-hyphen", "em-dash"],
            variable=self.dash_style_var,
        ).grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 14))

        format_frame = ctk.CTkFrame(self, corner_radius=12)
        format_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=10)
        ctk.CTkLabel(
            format_frame,
            text="STEP 2  FORMAT TRANSCRIPT",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        self.format_button = ctk.CTkButton(
            format_frame,
            text="Apply UFM Formatting",
            command=self.apply_formatting,
            width=180,
        )
        self.format_button.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))

        final_frame = ctk.CTkFrame(self, corner_radius=12)
        final_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=10)
        for column in range(4):
            final_frame.grid_columnconfigure(column, weight=1)
        ctk.CTkLabel(
            final_frame,
            text="STEP 3  FINALIZE OUTPUT",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 8))

        ctk.CTkCheckBox(final_frame, text="Apply Format Box", variable=self.show_format_box_var).grid(
            row=1, column=0, sticky="w", padx=14, pady=8
        )
        ctk.CTkCheckBox(final_frame, text="Apply Line Numbers", variable=self.show_line_numbers_var).grid(
            row=1, column=1, sticky="w", padx=14, pady=8
        )
        ctk.CTkCheckBox(final_frame, text="Apply Header", variable=self.show_header_var).grid(
            row=1, column=2, sticky="w", padx=14, pady=8
        )
        ctk.CTkCheckBox(final_frame, text="Apply Footer", variable=self.show_footer_var).grid(
            row=1, column=3, sticky="w", padx=14, pady=8
        )

        ctk.CTkLabel(final_frame, text="Header:").grid(row=2, column=0, sticky="w", padx=14, pady=(6, 4))
        self.header_entry = ctk.CTkEntry(final_frame, placeholder_text="Header text")
        self.header_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=14, pady=(6, 4))
        ctk.CTkLabel(final_frame, text="Footer:").grid(row=3, column=0, sticky="w", padx=14, pady=(4, 14))
        self.footer_entry = ctk.CTkEntry(final_frame, placeholder_text="Footer text")
        self.footer_entry.grid(row=3, column=1, columnspan=3, sticky="ew", padx=14, pady=(4, 14))

        export_frame = ctk.CTkFrame(self, corner_radius=12)
        export_frame.grid(row=4, column=0, sticky="ew", padx=18, pady=10)
        export_frame.grid_columnconfigure(0, weight=1)
        export_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(export_frame, text="EXPORT", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8)
        )
        self.export_draft_button = ctk.CTkButton(export_frame, text="Export Draft", command=self.export_draft)
        self.export_draft_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.export_final_button = ctk.CTkButton(export_frame, text="Export FINAL", command=self.export_final)
        self.export_final_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 14))

        content_frame = ctk.CTkFrame(self, corner_radius=12)
        content_frame.grid(row=5, column=0, sticky="nsew", padx=18, pady=(10, 18))
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(content_frame, text="Transcript Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(14, 8)
        )
        ctk.CTkLabel(content_frame, text="Status Panel", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=14, pady=(14, 8)
        )

        self.preview_text = ctk.CTkTextbox(content_frame, font=("Courier New", 13), wrap="word")
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

        status_panel = ctk.CTkFrame(content_frame, corner_radius=10)
        status_panel.grid(row=1, column=1, sticky="nsew", padx=14, pady=(0, 14))
        status_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(status_panel, textvariable=self.ai_status_var, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=12, pady=(14, 8)
        )
        ctk.CTkLabel(status_panel, textvariable=self.format_status_var, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=12, pady=8
        )
        ctk.CTkLabel(status_panel, textvariable=self.finalization_status_var, anchor="w").grid(
            row=2, column=0, sticky="ew", padx=12, pady=8
        )
        ctk.CTkLabel(status_panel, textvariable=self.status_var, anchor="w", wraplength=260, justify="left").grid(
            row=3, column=0, sticky="ew", padx=12, pady=(16, 14)
        )

    def upload_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select transcript file",
            filetypes=(
                ("Supported files", "*.txt *.docx *.pdf"),
                ("Text files", "*.txt"),
                ("Word documents", "*.docx"),
                ("PDF files", "*.pdf"),
            ),
        )
        if not file_path:
            return

        try:
            transcript = self.controller.load_file(file_path)
        except Exception as exc:
            LOGGER.exception("Failed to load transcript")
            self._show_error("Load Error", str(exc))
            return

        self.file_var.set(Path(file_path).name)
        self._set_preview_text(transcript)
        self.status_var.set("Transcript loaded. Run AI correction next.")
        self._sync_status_panel()
        self._refresh_buttons()

    def run_ai_correction(self) -> None:
        try:
            corrected = self.controller.run_ai_correction(
                proper_nouns=self._get_proper_nouns(),
                dash_style=self.dash_style_var.get(),
            )
        except Exception as exc:
            LOGGER.exception("AI correction failed")
            self._show_error("AI Error", str(exc))
            return

        self._set_preview_text(corrected)
        self.status_var.set("AI correction complete. Apply UFM formatting next.")
        self._sync_status_panel()
        self._refresh_buttons()

    def apply_formatting(self) -> None:
        try:
            formatted = self.controller.apply_formatting()
        except Exception as exc:
            LOGGER.exception("Formatting failed")
            self._show_error("Formatting Error", str(exc))
            return

        self._set_preview_text(formatted)
        self.status_var.set("Formatting applied. Configure finalization options and export.")
        self._sync_status_panel()
        self._refresh_buttons()

    def export_draft(self) -> None:
        try:
            export_path = self.controller.export_draft(
                header_text=self.header_entry.get().strip(),
                footer_text=self.footer_entry.get().strip(),
                show_line_numbers=self.show_line_numbers_var.get(),
                show_header=self.show_header_var.get(),
                show_footer=self.show_footer_var.get(),
            )
        except Exception as exc:
            LOGGER.exception("Draft export failed")
            self._show_error("Export Error", str(exc))
            return

        self.status_var.set(f"Draft export complete: {export_path}")
        self._sync_status_panel()
        self._refresh_buttons()
        self._show_info("Export Complete", f"Saved draft transcript to:\n{export_path}")

    def export_final(self) -> None:
        if not self.show_format_box_var.get():
            self.show_format_box_var.set(True)
            self.status_var.set("Final export requires the format box. It was enabled automatically.")

        try:
            export_path = self.controller.export_final(
                header_text=self.header_entry.get().strip(),
                footer_text=self.footer_entry.get().strip(),
                show_line_numbers=self.show_line_numbers_var.get(),
                show_header=self.show_header_var.get(),
                show_footer=self.show_footer_var.get(),
            )
        except Exception as exc:
            LOGGER.exception("Final export failed")
            self._show_error("Export Error", str(exc))
            return

        self.status_var.set(f"Final export complete: {export_path}")
        self._sync_status_panel()
        self._refresh_buttons()
        self._show_info("Export Complete", f"Saved final transcript to:\n{export_path}")

    def _get_proper_nouns(self) -> list[str]:
        raw_value = self.proper_nouns_text.get("1.0", "end").strip()
        if not raw_value:
            return []
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def _set_preview_text(self, text: str) -> None:
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)

    def _sync_status_panel(self) -> None:
        ai_status, formatting_status, finalization_status = self.controller.status_snapshot()
        self.ai_status_var.set(ai_status)
        self.format_status_var.set(formatting_status)
        self.finalization_status_var.set(finalization_status)

    def _refresh_buttons(self) -> None:
        state = self.controller.state
        has_source = bool(state.source_text.strip())
        self.format_button.configure(state="normal" if state.ai_completed else "disabled")
        self.export_draft_button.configure(state="normal" if state.formatting_applied else "disabled")
        self.export_final_button.configure(state="normal" if state.formatting_applied else "disabled")
        if not has_source:
            self.format_button.configure(state="disabled")
            self.export_draft_button.configure(state="disabled")
            self.export_final_button.configure(state="disabled")

    def _show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self)

    def _show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self)
