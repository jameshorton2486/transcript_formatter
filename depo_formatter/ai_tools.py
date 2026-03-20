import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from app_logging import get_logger


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL_CANDIDATES = [
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
]
VALID_DASH_STYLES = {"em-dash", "double-hyphen"}
MAX_CHUNK_CHARS = 12000
REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
APP_DIR = Path(__file__).resolve().parent
DOTENV_PATH = APP_DIR / ".env"


load_dotenv(dotenv_path=DOTENV_PATH)
LOGGER = get_logger(__name__)


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

Examples:

"Durens" -> "Duren" ONLY if confirmed in provided list.

"Neurospine Institute" -> standardize consistently.

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
"""


LEGAL_CORRECTION_DIRECTIVE = (
    "Apply only safe legal transcript correction under the rules above. "
    "Use the provided proper_nouns list and dash_style setting. "
    "Preserve verbatim testimony except where an explicit rule allows a minimal correction."
)

OUTPUT_REQUIREMENTS = """
OUTPUT REQUIREMENTS

Return ONLY the corrected transcript.

Preserve original structure and wording.

Do NOT include explanations, comments, or summaries.

Do NOT add extra text outside the transcript.
"""


def get_api_headers(api_key: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def post_messages_request(
    api_key: str,
    model_name: str,
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    max_tokens: int = 100,
) -> requests.Response:
    LOGGER.info("Posting Anthropic request with model=%s max_tokens=%s", model_name, max_tokens)
    print(f"[AI] Posting Anthropic request with model={model_name}")
    payload: dict[str, object] = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_prompt:
        payload["system"] = system_prompt

    return requests.post(
        ANTHROPIC_API_URL,
        headers=get_api_headers(api_key),
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def post_messages_request_with_retry(
    api_key: str,
    model_name: str,
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    max_tokens: int = 100,
    retries: int = MAX_RETRIES,
) -> requests.Response:
    last_exception: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            LOGGER.info(
                "Anthropic request attempt %s/%s model=%s max_tokens=%s",
                attempt,
                retries,
                model_name,
                max_tokens,
            )
            return post_messages_request(
                api_key,
                model_name,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
            )
        except requests.RequestException as exc:
            last_exception = exc
            LOGGER.warning(
                "Anthropic request attempt %s/%s failed for model=%s: %s",
                attempt,
                retries,
                model_name,
                exc,
            )
            print(f"[AI] Retry {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(RETRY_DELAY_SECONDS)

    raise ValueError(f"Anthropic request failed after {retries} attempts.") from last_exception


def extract_error_type(response: requests.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    error = payload.get("error", {})
    if isinstance(error, dict):
        error_type = error.get("type")
        if isinstance(error_type, str):
            return error_type
    return None


def chunk_text_by_lines(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_text.split("\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1

        if current_lines and current_length + line_length > max_chars:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_length = line_length
            continue

        if not current_lines and line_length > max_chars:
            chunks.append(line)
            continue

        current_lines.append(line)
        current_length += line_length

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks if chunks else [normalized_text]


def find_available_model(api_key: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []

    for model_name in MODEL_CANDIDATES:
        LOGGER.info("Testing Anthropic model candidate: %s", model_name)
        response = post_messages_request_with_retry(
            api_key,
            model_name,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=20,
        )

        if response.ok:
            LOGGER.info("Anthropic model candidate succeeded: %s", model_name)
            return model_name, errors

        error_type = extract_error_type(response)
        if response.status_code == 404 or error_type == "not_found_error":
            LOGGER.warning("Anthropic model candidate not found: %s", model_name)
            errors.append(f"{model_name}: not found")
            continue

        LOGGER.error(
            "Anthropic model candidate failed: %s status=%s body=%s",
            model_name,
            response.status_code,
            response.text[:500],
        )
        errors.append(f"{model_name}: HTTP {response.status_code}")
        return None, errors

    return None, errors


def test_anthropic_connection() -> dict[str, str | int]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")

    LOGGER.info("Starting Anthropic connection test")
    model_name, attempts = find_available_model(api_key)
    if not model_name:
        LOGGER.error("Anthropic connection test failed. Attempts: %s", "; ".join(attempts))
        raise ValueError("No configured Anthropic model was available. Attempts: " + "; ".join(attempts))

    response = post_messages_request_with_retry(
        api_key,
        model_name,
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100,
    )

    result: dict[str, str | int] = {
        "status_code": response.status_code,
        "ok": "true" if response.ok else "false",
        "model": model_name,
    }

    try:
        payload = response.json()
        result["body"] = json.dumps(payload, ensure_ascii=False, indent=2)
    except ValueError:
        result["body"] = response.text.strip() or "<empty response body>"

    LOGGER.info(
        "Anthropic connection test completed with status=%s model=%s",
        response.status_code,
        model_name,
    )
    return result


def run_ai_text_chunks(
    transcript_text: str,
    system_prompt: str,
    proper_nouns: list[str] | None = None,
    dash_style: str = "double-hyphen",
    validate_chunk=None,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")

    if not transcript_text.strip():
        raise ValueError("There is no text to send to AI.")

    if dash_style not in VALID_DASH_STYLES:
        raise ValueError('dash_style must be "em-dash" or "double-hyphen".')

    model_name, attempts = find_available_model(api_key)
    if not model_name:
        LOGGER.error("No Anthropic model available. Attempts: %s", "; ".join(attempts))
        raise ValueError("No configured Anthropic model was available. Attempts: " + "; ".join(attempts))

    chunks = chunk_text_by_lines(transcript_text)
    LOGGER.info("Processing transcript in %s chunk(s)", len(chunks))
    print(f"[AI] Processing transcript in {len(chunks)} chunk(s)")

    results: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        LOGGER.info("Processing AI chunk %s/%s chars=%s", index, len(chunks), len(chunk))
        print(f"[AI] Processing chunk {index}/{len(chunks)}")
        payload_text = json.dumps(
            {
                "transcript": chunk,
                "proper_nouns": proper_nouns or [],
                "dash_style": dash_style,
            },
            ensure_ascii=False,
            indent=2,
        )

        response = post_messages_request_with_retry(
            api_key,
            model_name,
            messages=[{"role": "user", "content": payload_text}],
            system_prompt=system_prompt,
            max_tokens=4000,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.exception("Anthropic chunk request failed for chunk %s/%s", index, len(chunks))
            raise ValueError(
                f"Anthropic request failed for chunk {index}/{len(chunks)} "
                f"with status {response.status_code}: {response.text}"
            ) from exc

        payload = response.json()
        content = payload.get("content", [])
        if not content:
            LOGGER.error("Anthropic chunk response missing content. chunk=%s payload=%s", index, payload)
            raise ValueError(f"Anthropic response did not include any content for chunk {index}/{len(chunks)}.")

        text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
        result = "\n".join(block for block in text_blocks if block.strip()).strip()
        if not result:
            LOGGER.error("Anthropic chunk response missing usable text. chunk=%s payload=%s", index, payload)
            raise ValueError(
                f"Anthropic response did not include usable text for chunk {index}/{len(chunks)}."
            )

        if validate_chunk:
            validate_chunk(chunk, result)

        results.append(result)

    return "\n".join(results)


def run_ai_tool(
    transcript_text: str,
    proper_nouns: list[str] | None = None,
    dash_style: str = "double-hyphen",
) -> str:
    LOGGER.info(
        "Running legal correction. transcript_chars=%s proper_nouns=%s dash_style=%s",
        len(transcript_text),
        len(proper_nouns or []),
        dash_style,
    )
    system_prompt = f"{BASE_SYSTEM_PROMPT}\n{LEGAL_CORRECTION_DIRECTIVE}\n{OUTPUT_REQUIREMENTS}"
    result = run_ai_text_chunks(
        transcript_text,
        system_prompt=system_prompt,
        proper_nouns=proper_nouns,
        dash_style=dash_style,
    )
    LOGGER.info("Legal correction completed successfully output_chars=%s", len(result))
    return result
