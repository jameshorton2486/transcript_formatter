"""
app_logging.py - Enhanced logging for Depo Transcript Formatter.

Upgrades from original:
  - Structured log directory: logs/app.log, logs/errors.log, logs/ai.log, logs/formatting.log
  - Module-specific loggers route to the correct log file automatically
  - Thread-safe CTk GUI handler support via add_gui_handler()
  - Duplicate-handler guard (safe to call configure_logging() multiple times)
  - Session ID logged at startup for correlating log entries across a run

Usage (existing code unchanged):
    from app_logging import get_logger
    LOGGER = get_logger(__name__)        # works exactly as before

Add GUI panel handler after UI is built:
    from app_logging import add_gui_handler
    add_gui_handler(self._log_text_widget)
"""

import logging
import uuid
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LOGS_DIR = APP_DIR / "logs"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"

SESSION_ID = str(uuid.uuid4())[:8]

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return

    file_fmt = logging.Formatter(LOG_FORMAT)
    brief_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt=DATE_FORMAT,
    )

    app_handler = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
    app_handler.setFormatter(file_fmt)
    app_handler.setLevel(logging.INFO)

    err_handler = logging.FileHandler(LOGS_DIR / "errors.log", encoding="utf-8")
    err_handler.setFormatter(file_fmt)
    err_handler.setLevel(logging.ERROR)

    ai_handler = logging.FileHandler(LOGS_DIR / "ai.log", encoding="utf-8")
    ai_handler.setFormatter(file_fmt)
    ai_handler.setLevel(logging.DEBUG)

    fmt_handler = logging.FileHandler(LOGS_DIR / "formatting.log", encoding="utf-8")
    fmt_handler.setFormatter(file_fmt)
    fmt_handler.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setFormatter(brief_fmt)
    console.setLevel(logging.INFO)

    root.setLevel(logging.DEBUG)
    root.addHandler(app_handler)
    root.addHandler(err_handler)
    root.addHandler(console)

    ai_logger = logging.getLogger("ai_tools")
    ai_logger.addHandler(ai_handler)

    fmt_logger = logging.getLogger("formatter")
    fmt_logger.addHandler(fmt_handler)

    exp_logger = logging.getLogger("docx_exporter")
    exp_logger.addHandler(fmt_handler)

    root.info("Session %s started | logs  %s", SESSION_ID, LOGS_DIR)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Configures logging on first call."""
    configure_logging()
    return logging.getLogger(name)


def add_gui_handler(text_widget) -> None:
    """
    Attach a thread-safe CTk/Tk text widget as a live log output.

    Call this once after the UI is fully built:
        from app_logging import add_gui_handler
        add_gui_handler(self._log_textbox)

    The handler is added to the root logger so ALL modules emit to it.
    Uses widget.after(0, ...) to ensure thread safety.
    Level is set to INFO so debug noise stays out of the GUI panel.
    """
    configure_logging()

    handler = _CTkLogHandler(text_widget)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-5s  %(message)s",
            datefmt=DATE_FORMAT,
        )
    )
    handler.setLevel(logging.INFO)

    root = logging.getLogger()

    for existing_handler in root.handlers:
        if isinstance(existing_handler, _CTkLogHandler):
            return

    root.addHandler(handler)
    root.info("Live debug panel connected")


class _CTkLogHandler(logging.Handler):
    """
    Thread-safe log handler that writes to a CTkTextbox widget.

    Uses widget.after(0, fn) so log records emitted from background
    threads (AI calls, etc.) are safely delivered on the Tk main thread.

    Color tags for log levels are applied when the widget supports them
    (CTkTextbox does not expose tag_config, so color is done via prefix
    characters instead  readable without extra CTk internals).
    """

    LEVEL_PREFIX = {
        logging.DEBUG: "  ",
        logging.INFO: "  ",
        logging.WARNING: "  ",
        logging.ERROR: "  ",
        logging.CRITICAL: "  ",
    }

    def __init__(self, widget):
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            prefix = self.LEVEL_PREFIX.get(record.levelno, "  ")
            line = f"{prefix} {msg}\n"
            self._widget.after(0, self._append, line)
        except Exception:
            self.handleError(record)

    def _append(self, line: str) -> None:
        try:
            self._widget.configure(state="normal")
            self._widget.insert("end", line)
            self._widget.configure(state="disabled")
            self._widget.yview("end")
        except Exception:
            pass
