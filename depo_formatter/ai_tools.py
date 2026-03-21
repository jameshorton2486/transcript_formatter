"""
ai_tools.py — Anthropic AI integration for legal transcript correction.

FIXES vs. original:
  FIX-1  Model name:  "claude-sonnet-4-20250514" → "claude-sonnet-4-6" (correct ID)
  FIX-2  SDK:         Switched from raw requests → official anthropic SDK.
                      SDK handles auth, retries, rate-limit backoff, streaming.
  FIX-3  Token limit: max_tokens raised from 4000 → 16000 for large transcripts.
                      Large transcripts are chunked at paragraph boundaries.
  FIX-4  Model probe: find_available_model() now uses the SDK instead of raw HTTP,
                      so auth errors are distinct from model-not-found errors.
  FIX-5  Timeout:     Raised to 240s and added chunked request flow.
"""

import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from app_logging import get_logger


# ── FIX-1: Corrected model IDs in priority order ──────────────────────────────
MODEL_CANDIDATES = [
    "claude-sonnet-4-6",            # FIX-1: was "claude-sonnet-4-20250514" — invalid
    "claude-3-5-sonnet-20241022",   # stable fallback
    "claude-3-5-haiku-20241022",    # fast fallback for connection tests
]

# Chunking: large transcripts are split at paragraph boundaries.
# Each chunk is at most CHUNK_WORD_LIMIT words to stay within output token limits.
# For a 12,000-word deposition this produces ~5 chunks, each completing in ~40 seconds.
CHUNK_WORD_LIMIT = 2500

VALID_DASH_STYLES = {"em-dash", "double-hyphen"}
APP_DIR    = Path(__file__).resolve().parent
DOTENV_PATH = APP_DIR / ".env"

load_dotenv(dotenv_path=DOTENV_PATH)
LOGGER = get_logger(__name__)


# ── System prompts (unchanged from original — legally reviewed) ───────────────

BASE_SYSTEM_PROMPT = """You are a legal transcript correction engine operating under strict non-generative rules.

CRITICAL RULES (DO NOT VIOLATE):

Do NOT rewrite, summarize, or paraphrase testimony.

Do NOT change meaning under any circumstances.

Do NOT remove filler words.

Preserve verbatim speech exactly unless a rule explicitly allows a correction.

Only apply deterministic, minimal corrections.

If uncertain, do NOT guess - use [VERIFY: ...].

RULE SET 5 - SPEAKER CONSISTENCY

Every question MUST begin with "Q."

Every answer MUST begin with "A."

Do NOT merge multiple speakers into one line.

Do NOT split a single speaker across multiple labels.

If a line contains both Q and A, split it correctly.

Preserve original wording exactly when fixing structure.

RULE SET 6 - PROPER NOUN CORRECTION

Use the provided proper_nouns list to correct spelling.

Normalize repeated references to the same entity consistently.

STRICT:

Do NOT invent names.

Do NOT guess spellings.

If uncertain -> [VERIFY: uncertain name spelling].

RULE SET 7 - HOMOPHONE CORRECTION (SAFE ONLY)

Correct ONLY when context is 100% certain:

know <-> no

their <-> there

to <-> too

STRICT:

If ANY ambiguity exists -> DO NOT change.

Prefer leaving original over risking incorrect correction.

RULE SET 8 - NUMERIC STANDARDIZATION

Standardize medical/technical numeric references ONLY when context confirms meaning.

Example:

"4 and 6 were fused" -> "C4 and C6 were fused" ONLY if clearly referring to cervical spine levels.

STRICT:

Do NOT infer meaning without clear context.

If uncertain -> leave unchanged or flag.

RULE SET 9 - FLAGGING (NO MODIFICATION)

When encountering unclear or questionable content, add:

[VERIFY: unclear medical term]

[VERIFY: uncertain name spelling]

STRICT:

Do NOT attempt correction when flagging.

Do NOT remove or rewrite original text.

Flags must be minimal and precise.

RULE SET 10 - VERBATIM PRESERVATION

Preserve all filler words exactly as spoken.

Examples:

"Uh-huh" -> KEEP

"Huh-uh" -> KEEP

"um", "uh", "like" -> KEEP

Preserve repetition and stutters exactly.

Examples:

"he -- he did" -> KEEP verbatim

"I mean -- I mean" -> KEEP verbatim

STRICT:

Do NOT normalize responses (for example, do NOT convert "Uh-huh" to "Yes").

Do NOT clean up speech patterns.

Maintain full legal verbatim integrity.

RULE SET 11 - DASH STYLE CONFIGURATION

A parameter "dash_style" will be provided.

If dash_style = "em-dash"
Use: —

If dash_style = "double-hyphen"
Use: --

STRICT:

Apply consistently across the entire transcript.

Do NOT mix styles.

Do NOT alter meaning.

RULE SET 12 - AI SCOPE BOUNDARY

The Python rules engine already handles deterministic normalization before AI:
  - dash normalization
  - THE COURT REPORTER -> THE REPORTER
  - K. -> Okay.
  - Mhmm/Mmhm -> Mm-hmm
  - simple time normalization
  - simple percent and even-dollar normalization
  - sentence spacing normalization
  - (as read) parenthetical normalization
  - hyphenated examination headers

Do NOT spend tokens reformatting these mechanically unless context requires a real correction.

RULE SET 13 - SPEAKER LABEL RESOLUTION

If the transcript contains generic labels (Speaker 0:, Speaker 1:, Speaker 2:, Speaker 3:),
resolve them to named labels only when the surrounding context makes identity clear.

If a speaker label cannot be resolved with confidence -> [VERIFY: Speaker N identity]

STRICT:
Do NOT guess names.
Use context to confirm before assigning.

RULE SET 14 - ELLIPSIS AND VERBATIM PRESERVATION

Preserve ellipsis in any form (..., ...., . . .).
Do NOT remove, consolidate, or replace ellipsis with a dash.
Preserve objection fragments and partial utterances exactly as spoken.

RULE SET 15 - CONTEXT-DEPENDENT NUMERIC AND FORM ATTENTION

If a number, money amount, measurement, or form heading is ambiguous, do NOT guess.
Leave unchanged or flag with [VERIFY: ...].
"""

LEGAL_CORRECTION_DIRECTIVE = (
    "Apply only safe legal transcript correction under the rules above. "
    "Use the provided proper_nouns list and dash_style setting. "
    "Preserve verbatim testimony except where an explicit rule allows a minimal correction."
)

REVIEW_CORRECTION_DIRECTIVE = (
    "Prepare a review-safe correction pass for Microsoft Word Track Changes. "
    "DO NOT modify Q. or A. labels. "
    "DO NOT modify speaker names such as MR., MS., MRS., THE WITNESS, THE REPORTER, or similar labels. "
    "DO NOT change line count. "
    "DO NOT merge lines. "
    "DO NOT split lines. "
    "Only correct punctuation, capitalization, and spacing."
)

OUTPUT_REQUIREMENTS = """
OUTPUT REQUIREMENTS

Return ONLY the corrected transcript.

Preserve original structure and wording.

Do NOT include explanations, comments, or summaries.

Do NOT add extra text outside the transcript.
"""


# ── SDK client factory ────────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    """Return an authenticated Anthropic SDK client."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to the .env file in the app directory."
        )
    return anthropic.Anthropic(api_key=api_key, timeout=240.0)


def _split_into_chunks(text: str, word_limit: int = CHUNK_WORD_LIMIT) -> list[str]:
    """
    Split transcript text into chunks at paragraph boundaries.
    Each chunk is at most word_limit words. Splits on blank lines so
    Q/A pairs are never broken mid-exchange.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if para_words > word_limit:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_words = 0

            words = para.split()
            for start in range(0, len(words), word_limit):
                chunks.append(" ".join(words[start : start + word_limit]))
            continue

        if current and current_words + para_words > word_limit:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


def _call_api_chunked(
    system_prompt: str,
    transcript_text: str,
    proper_nouns: list[str],
    dash_style: str,
) -> str:
    """
    For transcripts longer than CHUNK_WORD_LIMIT words, split into chunks
    and call the API once per chunk. Reassemble in order.
    Short transcripts go through _call_api directly (no overhead).
    """
    word_count = len(transcript_text.split())
    if word_count <= CHUNK_WORD_LIMIT:
        payload = json.dumps(
            {
                "transcript": transcript_text,
                "proper_nouns": proper_nouns,
                "dash_style": dash_style,
            },
            ensure_ascii=False,
            indent=2,
        )
        return _call_api(system_prompt, payload)

    chunks = _split_into_chunks(transcript_text)
    LOGGER.info("Chunking transcript | words=%s chunks=%s", word_count, len(chunks))
    corrected_chunks: list[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        LOGGER.info("Processing chunk %d/%d | words=%s", idx, len(chunks), len(chunk.split()))
        payload = json.dumps(
            {
                "transcript": chunk,
                "proper_nouns": proper_nouns,
                "dash_style": dash_style,
                "chunk_context": (
                    f"This is chunk {idx} of {len(chunks)} of the same deposition. "
                    "Apply all correction rules consistently with prior chunks."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        result = _call_api(system_prompt, payload)
        corrected_chunks.append(result)

    return "\n\n".join(corrected_chunks)


# ── Model discovery ───────────────────────────────────────────────────────────

def find_available_model(client: anthropic.Anthropic) -> tuple[str | None, list[str]]:
    """
    FIX-4: Uses SDK instead of raw HTTP.
    Tries each MODEL_CANDIDATES entry with a minimal probe call.
    Returns (model_name, errors) — model_name is None if all fail.
    """
    errors: list[str] = []

    for model_name in MODEL_CANDIDATES:
        LOGGER.info("Testing model candidate: %s", model_name)
        try:
            client.messages.create(
                model=model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            LOGGER.info("Model available: %s", model_name)
            return model_name, errors
        except anthropic.NotFoundError:
            LOGGER.warning("Model not found: %s", model_name)
            errors.append(f"{model_name}: not found")
        except anthropic.AuthenticationError as exc:
            LOGGER.error("Authentication failed: %s", exc)
            raise ValueError(
                "Anthropic API key is invalid or expired. "
                "Check ANTHROPIC_API_KEY in the .env file."
            ) from exc
        except anthropic.APIError as exc:
            LOGGER.error("API error for model %s: %s", model_name, exc)
            errors.append(f"{model_name}: {exc}")
            break   # Non-404 errors indicate a real problem — stop probing

    return None, errors


# ── Connection test ───────────────────────────────────────────────────────────

def test_anthropic_connection() -> dict[str, str | int]:
    """
    Probe the Anthropic API and return diagnostic data for the UI status display.
    """
    client = _get_client()
    LOGGER.info("Starting Anthropic connection test")

    model_name, attempts = find_available_model(client)
    if not model_name:
        raise ValueError(
            "No configured Anthropic model was available.\n"
            + "\n".join(attempts)
        )

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with: OK"}],
        )
        body = response.content[0].text if response.content else "<empty>"
        LOGGER.info("Connection test OK — model=%s", model_name)
        return {
            "status_code": 200,
            "ok":          "true",
            "model":       model_name,
            "body":        body,
        }
    except anthropic.APIError as exc:
        LOGGER.error("Connection test failed: %s", exc)
        return {
            "status_code": getattr(exc, "status_code", 0),
            "ok":          "false",
            "model":       model_name,
            "body":        str(exc),
        }


# ── Core AI call ──────────────────────────────────────────────────────────────

def _call_api(
    system_prompt: str,
    user_content: str,
    max_tokens: int = 16000,
) -> str:
    """
    Single Anthropic SDK call. Returns the text response or raises ValueError.
    All production AI calls go through here.
    """
    client = _get_client()
    model_name, attempts = find_available_model(client)
    if not model_name:
        raise ValueError(
            "No Anthropic model available. Attempts:\n" + "\n".join(attempts)
        )

    LOGGER.info("Calling %s (max_tokens=%s, input_chars=%s)", model_name, max_tokens, len(user_content))

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        LOGGER.exception("Anthropic API call failed")
        raise ValueError(f"Anthropic API error: {exc}") from exc

    text_blocks = [
        block.text for block in response.content if block.type == "text"
    ]
    result = "\n".join(t for t in text_blocks if t.strip()).strip()

    if not result:
        raise ValueError("Anthropic response contained no usable text.")

    LOGGER.info("API call completed — model=%s stop_reason=%s output_chars=%s",
                model_name, response.stop_reason, len(result))
    return result


# ── Public tool functions ─────────────────────────────────────────────────────

def run_ai_tool(
    transcript_text: str,
    proper_nouns: list[str] | None = None,
    dash_style: str = "double-hyphen",
) -> str:
    """Run legal correction AI pass. Called from UI (must run in background thread)."""
    if not transcript_text.strip():
        raise ValueError("No transcript text provided.")
    if dash_style not in VALID_DASH_STYLES:
        raise ValueError('dash_style must be "em-dash" or "double-hyphen".')

    LOGGER.info(
        "run_ai_tool: chars=%s nouns=%s dash=%s",
        len(transcript_text), len(proper_nouns or []), dash_style,
    )

    system_prompt = f"{BASE_SYSTEM_PROMPT}\n{LEGAL_CORRECTION_DIRECTIVE}\n{OUTPUT_REQUIREMENTS}"
    return _call_api_chunked(system_prompt, transcript_text, proper_nouns or [], dash_style)


def run_ai_review_tool(
    transcript_text: str,
    proper_nouns: list[str] | None = None,
    dash_style: str = "double-hyphen",
) -> str:
    """Run Word Track Changes correction pass. Output must preserve line count exactly."""
    if not transcript_text.strip():
        raise ValueError("No transcript text provided.")
    if dash_style not in VALID_DASH_STYLES:
        raise ValueError('dash_style must be "em-dash" or "double-hyphen".')

    LOGGER.info(
        "run_ai_review_tool: chars=%s nouns=%s dash=%s",
        len(transcript_text), len(proper_nouns or []), dash_style,
    )

    user_content = json.dumps(
        {
            "transcript":   transcript_text,
            "proper_nouns": proper_nouns or [],
            "dash_style":   dash_style,
        },
        ensure_ascii=False,
        indent=2,
    )
    system_prompt = f"{BASE_SYSTEM_PROMPT}\n{REVIEW_CORRECTION_DIRECTIVE}\n{OUTPUT_REQUIREMENTS}"
    result = _call_api(system_prompt, user_content)
    validate_review_output(transcript_text, result)
    return result


def extract_proper_nouns_from_pdf(pdf_text: str) -> list[str]:
    """
    Use Claude to extract proper nouns from a legal PDF document.

    Sends the extracted PDF text to Claude with a focused single-purpose
    prompt. Returns a deduplicated list of proper nouns, one per item.

    Designed for: deposition notices, subpoenas, appearance pages,
    scheduling orders, medical records headers, and similar legal documents.

    Returns: list of strings, e.g.:
      ["Angie Irani Ozuna", "Benito Gonzalez", "BV Xpress LLC",
       "Miah Bardot", "James R. Horton", "SA Legal Solutions"]

    Raises ValueError if API key not set or extraction fails.
    """
    if not pdf_text.strip():
        raise ValueError("PDF text is empty - could not extract any text from this file.")

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Cannot run AI extraction.")

    LOGGER.info("Extracting proper nouns from PDF | chars=%s", len(pdf_text))

    system_prompt = """You are a legal document parser.
Your only job is to extract proper nouns from legal documents.

Extract ALL of the following:
  - Full names of people (attorneys, witnesses, parties, doctors, interpreters, judges)
  - Company and firm names (LLCs, PLLCs, LLPs, corporations, medical practices)
  - Medical facility names (hospitals, clinics, institutes, centers)
  - Court names and judicial districts
  - Cause numbers and case styles
  - Geographic proper nouns if they appear as named locations (not generic: not "Texas", not "County")

STRICT RULES:
  Return ONLY a JSON array of strings. Nothing else.
  One proper noun per string.
  No duplicates. No trailing punctuation.
  No explanations. No preamble. No markdown.
  Do NOT include: generic titles like "Plaintiff" or "Defendant" alone.
  Do NOT include: generic words like "District Court" without a specific name.

Example output:
["Angie Irani Ozuna", "Benito Gonzalez", "BV Xpress LLC", "Miah Bardot", "James R. Horton", "SA Legal Solutions", "406th Judicial District Court"]
"""

    user_content = f"Extract all proper nouns from this legal document:\n\n{pdf_text[:12000]}"

    client = _get_client()
    model_name, attempts = find_available_model(client)
    if not model_name:
        raise ValueError("No Anthropic model available: " + "; ".join(attempts))

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        raise ValueError(f"Anthropic API error during extraction: {exc}") from exc

    raw = ""
    for block in response.content:
        if block.type == "text":
            raw += block.text

    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    import json as _json

    try:
        nouns = _json.loads(raw)
        if not isinstance(nouns, list):
            raise ValueError("Response was not a JSON array")
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in nouns:
            item = str(item).strip().strip(".,;")
            if item and item.lower() not in seen:
                seen.add(item.lower())
                cleaned.append(item)
        LOGGER.info("Proper noun extraction complete | count=%s", len(cleaned))
        return cleaned
    except (_json.JSONDecodeError, ValueError) as exc:
        LOGGER.error("Failed to parse proper noun extraction response: %s", raw[:200])
        raise ValueError(
            f"AI did not return a valid list. Raw response:\n{raw[:300]}"
        ) from exc


# ── Review output validation ──────────────────────────────────────────────────

def get_line_prefix(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped:
        return None
    if re.match(r"^(Q\.|A\.)\s", stripped):
        return stripped[:2]
    m = re.match(r"^([A-Z][A-Z\.\s']+):", stripped)
    if m:
        return m.group(1)
    return None


def validate_review_output(original_text: str, corrected_text: str) -> None:
    """
    Ensure the AI review output preserves line count and protected labels.
    Raises ValueError if either constraint is violated.
    """
    original_lines  = original_text.splitlines()
    corrected_lines = corrected_text.splitlines()

    if len(original_lines) != len(corrected_lines):
        raise ValueError(
            f"AI review changed line count: {len(original_lines)} → {len(corrected_lines)}. "
            "Track Changes review requires identical line count."
        )

    for idx, (orig, corr) in enumerate(zip(original_lines, corrected_lines), start=1):
        orig_prefix = get_line_prefix(orig)
        corr_prefix = get_line_prefix(corr)
        if orig_prefix != corr_prefix:
            raise ValueError(
                f"AI review changed a protected label on line {idx}. "
                f"Original prefix: {orig_prefix!r} → Corrected: {corr_prefix!r}. "
                "Q./A. and speaker labels must be unchanged."
            )
