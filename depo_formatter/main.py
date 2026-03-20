import os
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from dotenv import load_dotenv

from app_logging import get_logger
from ai_tools import run_ai_tool, test_anthropic_connection
from docx_exporter import export_to_docx
from file_loader import LoadedTranscript, load_transcript
from formatter import format_transcript


APP_DIR = Path(__file__).resolve().parent
DOTENV_PATH = APP_DIR / ".env"
SESSION_PATH = APP_DIR / "session_state.json"
load_dotenv(dotenv_path=DOTENV_PATH)
LOGGER = get_logger(__name__)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class DepoTranscriptFormatterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Depo Transcript Formatter (AI-Assisted)")
        self.geometry("1040x760")
        self.minsize(820, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.loaded_file_path: str | None = None
        self.loaded_transcript: LoadedTranscript | None = None
        self.status_var = tk.StringVar(value="Load a transcript file to begin.")
        self.dash_style_var = tk.StringVar(value="double-hyphen")
        self.api_key_status_var = tk.StringVar(value=self.get_api_key_status_text())
        self.history: list[dict[str, str | None]] = []

        self._build_layout()
        self.restore_session()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top_frame.grid_columnconfigure(1, weight=1)

        upload_button = ctk.CTkButton(
            top_frame,
            text="Upload File",
            command=self.upload_file,
            width=160,
        )
        upload_button.grid(row=0, column=0, padx=12, pady=12)

        self.file_label = ctk.CTkLabel(top_frame, text="No transcript loaded", anchor="w")
        self.file_label.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        self.api_key_label = ctk.CTkLabel(
            top_frame,
            textvariable=self.api_key_status_var,
            anchor="e",
        )
        self.api_key_label.grid(row=0, column=2, sticky="e", padx=(0, 12))

        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        for column in range(4):
            button_frame.grid_columnconfigure(column, weight=1)

        ctk.CTkButton(
            button_frame,
            text="Format (Rules Engine)",
            command=self.run_rules_formatter,
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=12)

        ctk.CTkButton(
            button_frame,
            text="Legal Correction (AI)",
            command=self.run_legal_correction,
        ).grid(row=0, column=1, sticky="ew", padx=8, pady=12)

        ctk.CTkButton(
            button_frame,
            text="Reset",
            command=self.reset_last_action,
        ).grid(row=0, column=2, sticky="ew", padx=8, pady=12)

        ctk.CTkButton(
            button_frame,
            text="Test Anthropic Connection",
            command=self.run_connection_test,
        ).grid(row=0, column=3, sticky="ew", padx=8, pady=12)

        ai_config_frame = ctk.CTkFrame(self)
        ai_config_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        ai_config_frame.grid_columnconfigure(0, weight=3)
        ai_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ai_config_frame, text="Proper Nouns (one per line)").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        ctk.CTkLabel(ai_config_frame, text="Dash Style").grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 4)
        )

        self.proper_nouns_text = ctk.CTkTextbox(ai_config_frame, height=96, wrap="word")
        self.proper_nouns_text.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.proper_nouns_text.insert(
            "1.0",
            "Enrique Benavides\nGerardo Alba\nLuciano Hernandez\nAmerican Neurospine Institute",
        )

        dash_menu = ctk.CTkOptionMenu(
            ai_config_frame,
            values=["double-hyphen", "em-dash"],
            variable=self.dash_style_var,
        )
        dash_menu.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))

        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=8)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(preview_frame, text="Editable Transcript Preview").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 0)
        )

        self.preview_text = ctk.CTkTextbox(preview_frame, wrap="word", font=("Courier New", 13))
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(8, 16))
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(bottom_frame, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ctk.CTkButton(
            bottom_frame,
            text="Export to Word",
            command=self.export_docx,
            width=180,
        ).grid(row=1, column=0, sticky="e", padx=12, pady=(4, 12))

        ctk.CTkButton(
            bottom_frame,
            text="Clear",
            command=self.clear_session,
            width=120,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(4, 12))

    def upload_file(self) -> None:
        LOGGER.info("Upload button clicked")
        print("[UI] Upload button clicked")
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
            LOGGER.info("Upload cancelled by user")
            return

        try:
            loaded_transcript = load_transcript(file_path)
        except Exception as exc:
            LOGGER.exception("Failed to load transcript file: %s", file_path)
            self.show_error("Load Error", str(exc))
            return

        transcript = loaded_transcript.text
        if not transcript.strip():
            LOGGER.warning("Loaded transcript file was empty: %s", file_path)
            self.show_warning("Empty File", "The selected file did not contain extractable text.")
            return

        self.push_history()
        self.loaded_file_path = file_path
        self.loaded_transcript = loaded_transcript
        self.file_label.configure(text=Path(file_path).name)
        self.set_preview_text(transcript)
        self.status_var.set(self.build_loaded_status(Path(file_path).name, loaded_transcript))
        self.save_session()
        LOGGER.info("Loaded transcript file successfully: %s", file_path)

    def run_rules_formatter(self) -> None:
        LOGGER.info("Format button clicked")
        print("[UI] Format button clicked")
        text = self.get_preview_text()
        if not text.strip():
            self.show_warning("No Transcript", "Load a transcript before formatting.")
            return

        try:
            formatted = format_transcript(text, remove_fillers=False)
        except Exception as exc:
            LOGGER.exception("Formatting failed")
            self.show_error("Formatting Error", str(exc))
            return

        self.push_history()
        self.set_preview_text(formatted)
        self.status_var.set("Applied deterministic formatting rules without changing transcript wording.")
        self.save_session()
        LOGGER.info("Formatting completed successfully")

    def run_legal_correction(self) -> None:
        LOGGER.info("Legal Correction button clicked")
        print("[UI] Legal Correction button clicked")
        selected_text = self.get_selected_text()
        source_text = selected_text if selected_text.strip() else self.get_preview_text()

        if not source_text.strip():
            self.show_warning("No Transcript", "Load a transcript before using AI tools.")
            return

        title = "Legal Correction (AI)"
        self.status_var.set(f"Running {title}...")
        self.update_idletasks()

        try:
            ai_result = run_ai_tool(
                source_text,
                proper_nouns=self.get_proper_nouns(),
                dash_style=self.dash_style_var.get(),
            )
        except Exception as exc:
            LOGGER.exception("Legal correction failed")
            self.status_var.set("AI request failed.")
            self.show_error("AI Error", str(exc))
            return

        self.show_ai_result_dialog(title, ai_result, replace_selection=bool(selected_text.strip()))
        self.status_var.set(f"{title} result ready for review.")

    def run_connection_test(self) -> None:
        LOGGER.info("Test Anthropic Connection button clicked")
        print("[UI] Test Anthropic Connection button clicked")
        self.status_var.set("Testing Anthropic connection...")
        self.update_idletasks()

        try:
            result = test_anthropic_connection()
        except Exception as exc:
            LOGGER.exception("Anthropic connection test failed")
            self.status_var.set("Anthropic connection test failed.")
            self.show_error("Anthropic Test Error", str(exc))
            return

        status_code = result["status_code"]
        ok = result["ok"] == "true"
        body = str(result["body"])
        model = str(result.get("model", "unknown"))
        self.status_var.set(
            f"Anthropic test {'succeeded' if ok else 'failed'} with status {status_code} using {model}."
        )

        title = "Anthropic Connection Test"
        if ok:
            self.show_info(title, f"Status: {status_code}\nModel: {model}\n\nResponse:\n{body}")
        else:
            self.show_error(title, f"Status: {status_code}\nModel: {model}\n\nResponse:\n{body}")

    def show_ai_result_dialog(self, title: str, result_text: str, replace_selection: bool) -> None:
        LOGGER.info("Opening AI result dialog. replace_selection=%s", replace_selection)
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("900x640")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Review the AI output before applying it.",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        result_box = ctk.CTkTextbox(dialog, wrap="word", font=("Courier New", 13))
        result_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        result_box.insert("1.0", result_text)

        button_row = ctk.CTkFrame(dialog)
        button_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
        for column in range(3):
            button_row.grid_columnconfigure(column, weight=1)

        def apply_result() -> None:
            reviewed_text = result_box.get("1.0", "end").strip()
            self.push_history()
            if replace_selection:
                self.replace_selected_text(reviewed_text)
            else:
                self.set_preview_text(reviewed_text)
            self.status_var.set(f"Applied {title}.")
            self.save_session()
            LOGGER.info("Applied AI result")
            dialog.destroy()

        def clear_result() -> None:
            LOGGER.info("Clear button clicked in AI dialog")
            self.clear_session()
            dialog.destroy()

        ctk.CTkButton(button_row, text="Apply Result", command=apply_result).grid(
            row=0, column=0, sticky="ew", padx=8, pady=12
        )
        ctk.CTkButton(button_row, text="Cancel", command=dialog.destroy).grid(
            row=0, column=1, sticky="ew", padx=8, pady=12
        )
        ctk.CTkButton(button_row, text="Clear", command=clear_result).grid(
            row=0, column=2, sticky="ew", padx=8, pady=12
        )

    def export_docx(self) -> None:
        LOGGER.info("Export button clicked")
        print("[UI] Export button clicked")
        content = self.get_preview_text()
        if not content.strip():
            self.show_warning("Nothing to Export", "There is no transcript content to export.")
            return

        initial_name = "formatted_transcript.docx"
        if self.loaded_file_path:
            initial_name = f"{Path(self.loaded_file_path).stem}_formatted.docx"

        output_path = filedialog.asksaveasfilename(
            title="Save DOCX file",
            defaultextension=".docx",
            initialfile=initial_name,
            filetypes=(("Word Document", "*.docx"),),
        )
        if not output_path:
            LOGGER.info("Export cancelled by user")
            return

        try:
            final_path = export_to_docx(content, output_path)
        except Exception as exc:
            LOGGER.exception("Export failed")
            self.show_error("Export Error", str(exc))
            return

        self.status_var.set(f"Exported transcript to {Path(final_path).name}")
        self.show_info("Export Complete", f"Saved formatted transcript to:\n{final_path}")
        LOGGER.info("Export completed successfully: %s", final_path)

    def reset_last_action(self) -> None:
        LOGGER.info("Reset button clicked")
        print("[UI] Reset button clicked")
        if not self.history:
            self.show_info("Reset", "There is no previous action to undo.")
            return

        previous_state = self.history.pop()
        self.loaded_file_path = previous_state["loaded_file_path"]
        self.loaded_transcript = None
        self.file_label.configure(text=previous_state["file_label"] or "No transcript loaded")
        self.set_preview_text(previous_state["preview_text"] or "")
        self.status_var.set("Reverted the last text-changing action.")
        self.save_session()
        LOGGER.info("Reset completed")

    def clear_session(self) -> None:
        LOGGER.info("Clear button clicked")
        print("[UI] Clear button clicked")
        self.loaded_file_path = None
        self.loaded_transcript = None
        self.history.clear()
        self.file_label.configure(text="No transcript loaded")
        self.set_preview_text("")
        self.status_var.set("Cleared transcript and session state.")
        self.save_session()

    def save_session(self) -> None:
        try:
            payload = {
                "loaded_file_path": self.loaded_file_path,
                "preview_text": self.get_preview_text(),
                "file_label": self.file_label.cget("text"),
                "proper_nouns": self.get_proper_nouns(),
                "dash_style": self.dash_style_var.get(),
                "history": self.history,
            }
            SESSION_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            LOGGER.info("Saved session state")
        except Exception:
            LOGGER.exception("Failed to save session state")

    def restore_session(self) -> None:
        if not SESSION_PATH.exists():
            LOGGER.info("No prior session file found")
            return
        try:
            payload = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            self.loaded_file_path = payload.get("loaded_file_path")
            self.file_label.configure(text=payload.get("file_label") or "No transcript loaded")
            self.set_preview_text(payload.get("preview_text") or "")
            self.history = payload.get("history") or []
            proper_nouns = payload.get("proper_nouns") or []
            if proper_nouns:
                self.proper_nouns_text.delete("1.0", "end")
                self.proper_nouns_text.insert("1.0", "\n".join(proper_nouns))
            dash_style = payload.get("dash_style")
            if dash_style in {"double-hyphen", "em-dash"}:
                self.dash_style_var.set(dash_style)
            if self.get_preview_text():
                self.status_var.set("Restored previous session.")
            LOGGER.info("Restored prior session successfully")
        except Exception:
            LOGGER.exception("Failed to restore session state")
            self.status_var.set("Could not restore prior session.")

    def on_close(self) -> None:
        LOGGER.info("Application closing")
        self.save_session()
        self.destroy()

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
        self.history.append(
            {
                "loaded_file_path": self.loaded_file_path,
                "file_label": self.file_label.cget("text"),
                "preview_text": self.get_preview_text(),
            }
        )

    def get_proper_nouns(self) -> list[str]:
        raw_value = self.proper_nouns_text.get("1.0", "end").strip()
        if not raw_value:
            return []
        return [line.strip() for line in raw_value.splitlines() if line.strip()]

    def get_api_key_status_text(self) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return "Anthropic key: not loaded"
        if len(api_key) <= 8:
            return "Anthropic key: loaded"
        return f"Anthropic key: loaded ({api_key[:4]}...{api_key[-4:]})"

    def build_loaded_status(self, file_name: str, loaded_transcript: LoadedTranscript) -> str:
        if loaded_transcript.source_type != "docx" or not loaded_transcript.blocks:
            return f"Loaded {file_name}"

        speaker_map = loaded_transcript.speaker_map
        detected_roles: list[str] = []
        if speaker_map:
            role_values = {
                "witness": speaker_map.witness,
                "lead": speaker_map.lead_attorney,
                "opposing": speaker_map.opposing_attorney,
                "reporter": speaker_map.court_reporter,
                "video": speaker_map.videographer,
            }
            detected_roles = [f"{role}={sid}" for role, sid in role_values.items() if sid is not None]

        role_suffix = f" Detected {', '.join(detected_roles)}." if detected_roles else ""
        return (
            f"Loaded {file_name}. Parsed {len(loaded_transcript.blocks)} speaker blocks from DOCX."
            f"{role_suffix}"
        )

    def show_error(self, title: str, message: str) -> None:
        LOGGER.error("%s: %s", title, message)
        print(f"[ERROR] {title}: {message}")
        messagebox.showerror(title, message, parent=self)

    def show_warning(self, title: str, message: str) -> None:
        LOGGER.warning("%s: %s", title, message)
        print(f"[WARN] {title}: {message}")
        messagebox.showwarning(title, message, parent=self)

    def show_info(self, title: str, message: str) -> None:
        LOGGER.info("%s: %s", title, message)
        print(f"[INFO] {title}: {message}")
        messagebox.showinfo(title, message, parent=self)


if __name__ == "__main__":
    app = DepoTranscriptFormatterApp()
    app.mainloop()
