# Legal Transcript System

Legal Transcript System is a local Windows 11 desktop application for loading transcript files, applying deterministic formatting rules, optionally sending text to a constrained AI legal-correction engine on demand, reviewing the result, and exporting the final transcript to Word.

It combines two workflows already present in this repository:

- a desktop transcript workspace for loading, cleaning, reviewing, and exporting transcript text
- a CLI document builder for generating structured legal transcript packages from DOCX templates

## Features

- Loads transcript files from `.txt`, `.docx`, and `.pdf`
- Extracts raw text locally from each supported file type
- Applies non-AI transcript formatting rules
- Preserves an AI-before-format workflow in the desktop app so deterministic formatting remains the final step
- Offers one user-triggered AI action:
  - Legal Correction (AI)
- Shows AI output before any text is replaced
- Allows direct editing in the preview area
- Restores the last loaded transcript when the app is reopened
- Writes application activity and errors to `depo_formatter.log`
- Exports to `.docx` using Courier New 12pt
- Builds templated transcript packages through the repository root `main.py` CLI

## Install

```powershell
cd C:\Users\james\transcript_formatter\depo_formatter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

From the repository root you can also run the CLI transcript package builder:

```powershell
cd C:\Users\james\transcript_formatter
python main.py
```

## AI Setup

Set your Anthropic API key before launching the app:

1. Add your key to `.env`:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

2. Launch the app:

```powershell
python main.py
```

If `ANTHROPIC_API_KEY` is not set, the Legal Correction action will fail safely and show an error dialog.

The app sends AI requests with:

- `transcript`
- `proper_nouns`
- `dash_style`

You can edit `proper_nouns` directly in the app and choose either `double-hyphen` or `em-dash` for dash normalization.

## Formatting Rules Engine

The non-AI formatter:

- normalizes spacing
- preserves transcript wording
- applies `Q.` / `A.` formatting only when those labels already exist in the text
- wraps lines with a 5-space continuation indent
- inserts a blank line between sections
- is intended to finalize transcript structure after any optional AI review

The non-AI formatter does not:

- infer new speaker content
- alternate unlabeled sentences into `Q.` / `A.` pairs
- remove filler words automatically
- use AI or rewrite testimony

## File Support

- `TXT`: plain text file reading
- `DOCX`: Deepgram-aware paragraph parsing using `python-docx`
  - detects `Speaker N:` labels
  - assembles each speaker turn before sentence-based paragraph splitting
  - auto-detects likely witness, attorneys, court reporter, and videographer from the first 30 blocks
- `PDF`: text extraction using `pdfplumber`

## Deepgram DOCX Parsing

When a Word transcript uses Deepgram-style speaker labels, the loader now:

- detects speaker label paragraphs with `Speaker N:` matching
- accumulates all non-label paragraphs under the current speaker turn
- joins those fragments into a single block before re-splitting at sentence boundaries
- avoids false paragraph splits after common abbreviations like `Dr.` and `Mr.`
- builds a speaker-role map from the first 30 parsed blocks using keyword detection with count-based fallback

## Safety

- AI is never run automatically
- AI only runs when the user clicks `Legal Correction (AI)`
- AI output is shown in a review window before applying it
- Prompts instruct the model not to rewrite, summarize, paraphrase, or remove testimony
- Filler words are preserved unless you manually approve AI output that changes them

## Session Behavior

- Loaded transcript text is saved locally and restored when the app restarts
- Use the `Clear` button to remove the current transcript from the app
- Session state is stored in `session_state.json`

## Logging

- Runtime logs are written to `depo_formatter.log`
- Button clicks, API requests, and error conditions are logged
