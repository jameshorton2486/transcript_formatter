"""GUI entrypoint for the legal transcript system."""

from __future__ import annotations

from transcript_formatter.app.ui.main_window import LegalTranscriptSystemApp


def main() -> None:
    app = LegalTranscriptSystemApp()
    app.mainloop()


if __name__ == "__main__":
    main()
