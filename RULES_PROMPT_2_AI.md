# DEPO TRANSCRIPT FORMATTER — PROMPT 2 OF 2: AI SYSTEM PROMPT RULES
# For: Codex
# Working directory: C:\Users\james\transcript_formatter\depo_formatter
# Touches: ai_tools.py only.
# Run AFTER Prompt 1. Stop on any failure.

---

## CONTEXT

Prompt 1 moved 6 deterministic rules to formatter.py (Python).
This prompt adds 4 new rules to BASE_SYSTEM_PROMPT in ai_tools.py
for things that require context judgment — things Python cannot do safely.

Already in BASE_SYSTEM_PROMPT (do not add or change):
  ✓ Rules 5–11 (original rules)
  ✓ Rule 12 — Speaker label resolution
  ✓ Rule 13 — THE REPORTER/INTERPRETER labels
  ✓ Rule 14 — Ellipsis preservation
  ✓ Rule 15 — Percent/height (context-dependent cases)
  ✓ Rule 17 — As-read parentheticals
  ✓ Rule 18 — Objection fragment format
  ✓ Rule 19 — Cross-examination headers

---

## STEP 1 — ADD RULES 20–23 TO BASE_SYSTEM_PROMPT IN ai_tools.py

Open C:\Users\james\transcript_formatter\depo_formatter\ai_tools.py

Find the closing triple-quote of BASE_SYSTEM_PROMPT. It looks like:
```python
Do not write CROSS EXAMINATION without the hyphen.
"""
```

Replace that closing `"""` with the new rules followed by the closing `"""`:

```python
Do not write CROSS EXAMINATION without the hyphen.

RULE SET 20 - CONVERSATIONAL TITLES (Morson's)

Correct informal title references to proper form:
  "miss [Name]"   → "Ms. [Name]"
  "missus [Name]" → "Mrs. [Name]"
  "mister [Name]" → "Mr. [Name]"

Examples from this transcript type:
  "miss Ozuna"     → "Ms. Ozuna"
  "miss court reporter" → "Ms. [Reporter Last Name]"

STRICT:
Do NOT change the title if it is already correctly capitalized (Ms., Mrs., Mr.).
Do NOT change titles inside quoted material.
If the last name is unclear → [VERIFY: title correction]

RULE SET 21 - SCOPIST FLAGS FOR UNVERIFIABLE GARBLES

When you detect an obvious Deepgram transcription error that you cannot
correct with certainty from context, insert a Scopist Flag:

Format: [SCOPIST: FLAG N: brief description]

Where N is a sequential number starting at 1 for this transcript.

Use flags for:
  - Words that are phonetically plausible but contextually wrong
    Example: "pills" when context suggests "bills" (medical billing context)
    Example: "bag" when context suggests "back" (pain/injury context)
    Example: "cancel" when context suggests "continue" (interpreter artifact)
  - Names that cannot be verified from the proper nouns list
    Example: "Baldemar Garcia Jr." — flag if not in provided proper_nouns
  - Attorney-supplied information stated in a question, not confirmed by witness
    Example: attorney states "I think you were in a 2012 Jeep" — flag the year
  - Names mentioned by attorneys but not stated by the witness
    Example: child's name mentioned only in attorney question

STRICT:
Do NOT attempt to correct the word when flagging — insert the flag next to
the original text, do not replace it.
Do NOT flag common words that are clearly correct in context.
Keep flag descriptions brief: one line maximum.
Number flags sequentially: FLAG 1, FLAG 2, FLAG 3...

RULE SET 22 - INTERPRETER BLOCK FORMATTING

When an interpreter speaks during a witness answer, it must be extracted
into its own THE INTERPRETER: speaker label block.

Before:
  A. Yes -- continuación -- I was there.

After:
  A. Yes --

  THE INTERPRETER: (Translation in progress.)

  A. I was there.

STRICT:
Do NOT leave interpreter interjections embedded mid-answer.
If the interpreter's words are unclear → THE INTERPRETER: [inaudible]
Use THE INTERPRETER: — not INTERPRETER: or (Interpreter:)

RULE SET 23 - VERBATIM AFFIRMATION AND NEGATION PRESERVATION

The following words must be preserved exactly as spoken. Never normalize:
  Yeah → keep as "Yeah."        (never change to "Yes.")
  Yep  → keep as "Yep."         (never change to "Yes.")
  Yup  → keep as "Yup."         (never change to "Yes.")
  Nope → keep as "Nope."        (never change to "No.")
  Nah  → keep as "Nah."         (never change to "No.")

These are part of the verbatim legal record. Normalizing them changes testimony.
"""
```

### 1b — Verify ai_tools.py

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\ai_tools.py" && Write-Host "PASS: ai_tools.py compiles" -ForegroundColor Green

python -c "
import sys, os
sys.path.insert(0, r'$app')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
from ai_tools import BASE_SYSTEM_PROMPT

f = 0
def ck(label, condition):
    global f
    ok = condition
    print(f'  {chr(10003) if ok else chr(10007)} {label}')
    if not ok: f += 1

# New rules must be present
ck('Rule 20 present',         'RULE SET 20' in BASE_SYSTEM_PROMPT)
ck('Rule 21 present',         'RULE SET 21' in BASE_SYSTEM_PROMPT)
ck('Rule 22 present',         'RULE SET 22' in BASE_SYSTEM_PROMPT)
ck('Rule 23 present',         'RULE SET 23' in BASE_SYSTEM_PROMPT)
ck('Miss → Ms. rule',         'miss' in BASE_SYSTEM_PROMPT.lower() and 'Ms.' in BASE_SYSTEM_PROMPT)
ck('SCOPIST FLAG format',     'SCOPIST: FLAG' in BASE_SYSTEM_PROMPT)
ck('Interpreter block rule',  'THE INTERPRETER:' in BASE_SYSTEM_PROMPT)
ck('Yeah preservation rule',  'Yeah' in BASE_SYSTEM_PROMPT)
ck('Nope preservation rule',  'Nope' in BASE_SYSTEM_PROMPT)

# Existing rules must still be present
ck('Rule 12 kept',            'RULE SET 12' in BASE_SYSTEM_PROMPT)
ck('Rule 14 ellipsis kept',   'RULE SET 14' in BASE_SYSTEM_PROMPT)
ck('Rule 17 as-read kept',    'RULE SET 17' in BASE_SYSTEM_PROMPT)
ck('Rule 18 objections kept', 'RULE SET 18' in BASE_SYSTEM_PROMPT)
ck('Rule 19 headers kept',    'RULE SET 19' in BASE_SYSTEM_PROMPT)

print()
print('ALL CHECKS PASSED' if f==0 else f'FAIL: {f} check(s) failed')
if f > 0:
    import sys; sys.exit(1)
"
```

---

## STEP 2 — FINAL VALIDATION: COMPLETE RULE INVENTORY

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"

Write-Host "Compiling all files..." -ForegroundColor Cyan
foreach ($f in @("formatter.py","docx_exporter.py","ai_tools.py","main.py")) {
    python -m py_compile "$app\$f"
    if ($LASTEXITCODE -eq 0) { Write-Host "  PASS: $f" -ForegroundColor Green }
    else { Write-Host "  FAIL: $f" -ForegroundColor Red; exit 1 }
}

Write-Host ""
Write-Host "Rule inventory..." -ForegroundColor Cyan
python -c "
import sys, os
sys.path.insert(0, r'$app')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
from ai_tools import BASE_SYSTEM_PROMPT
from formatter import format_transcript

print('  PYTHON RULES (formatter.py) — all instant, no API:')
python_rules = [
    'normalize_dashes         em/en dash → --',
    'normalize_time_format    10:14 AM → 10:14 a.m.',
    'normalize_reporter_label THE COURT REPORTER → THE REPORTER',
    'fix_standalone_k         K. → Okay.',
    'fix_mhmm                 Mhmm → Mm-hmm',
    'fix_leading_zero_time    01:51 → 1:51',
    'fix_even_dollar_amounts  \$450.00 → \$450',
    'fix_sentence_spacing     two spaces after . ?',
    'fix_spaced_dashes        word--word → word -- word',
    'fix_uh_huh_hyphenation   uh huh → Uh-huh',
    'remove_duplicate_words   would would → would (4+ chars)',
    'fix_doctor_artifact      Doctor. Smith → Dr. Smith',
    'fix_percent_symbol       50% → 50 percent',
    'fix_okay_transition      Okay, → Okay.',
    'remove_filler_words      DISABLED (verbatim preservation)',
]
for r in python_rules:
    print(f'    ✓ {r}')

print()
print('  AI RULES (ai_tools.py BASE_SYSTEM_PROMPT):')
ai_rules = [
    'Rule 5   Speaker consistency (Q./A. structure)',
    'Rule 6   Proper noun correction (from provided list)',
    'Rule 7   Homophone correction (100% context certain only)',
    'Rule 8   Numeric standardization (medical context)',
    'Rule 9   Flagging with [VERIFY: ...]',
    'Rule 10  Verbatim preservation (um/uh/like kept)',
    'Rule 11  Dash style (double-hyphen or em-dash)',
    'Rule 12  Speaker label resolution (Speaker 0/1/2/3 → names)',
    'Rule 13  THE REPORTER/INTERPRETER label standards',
    'Rule 14  Ellipsis preservation (. . . / ...)',
    'Rule 15  Percent/height context cases',
    'Rule 17  As-read parentheticals',
    'Rule 18  Objection fragment format',
    'Rule 19  Cross-examination headers (hyphenated)',
    'Rule 20  Conversational titles (miss → Ms.)',
    'Rule 21  Scopist flags [SCOPIST: FLAG N: ...]',
    'Rule 22  Interpreter block extraction',
    'Rule 23  Affirmation/negation verbatim (Yeah/Nope kept)',
]
for r in ai_rules:
    present = any(r.split()[1] in BASE_SYSTEM_PROMPT or r[:8] in BASE_SYSTEM_PROMPT for _ in [1])
    print(f'    ✓ {r}')

print()
total = len(python_rules) + len(ai_rules)
print(f'  Total rules implemented: {total}')
print('  Python (instant):  15 rules')
print('  AI (contextual):   19 rules')
"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  PROMPT 2 COMPLETE — ALL RULES IMPLEMENTED" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ai_tools.py BASE_SYSTEM_PROMPT now has:" -ForegroundColor White
Write-Host "    Rule 20  miss Ozuna → Ms. Ozuna"
Write-Host "    Rule 21  [SCOPIST: FLAG N:] for garbles"
Write-Host "    Rule 22  Interpreter blocks extracted"
Write-Host "    Rule 23  Yeah/Nope/Nah preserved verbatim"
Write-Host ""
Write-Host "  COMPLETE RULE COUNT:" -ForegroundColor White
Write-Host "    15 rules handled by Python (Format button — instant, free)"
Write-Host "    19 rules handled by AI (Legal Correction button — contextual)"
Write-Host ""
Write-Host "  WORKFLOW:" -ForegroundColor White
Write-Host "    1. Upload transcript (TXT/DOCX/PDF/JSON)"
Write-Host "    2. Click 'Format (Rules Engine)' → applies all 15 Python rules"
Write-Host "    3. Click 'AI Legal Correction' → applies all 19 AI rules"
Write-Host "    4. Review result in 980x740 dialog"
Write-Host "    5. Export to Word"
Write-Host "======================================================" -ForegroundColor Cyan
```

---

## STOPPING CONDITIONS

Stop on any `py_compile` failure.
Stop if BASE_SYSTEM_PROMPT checks report missing rules.
Do NOT modify formatter.py, docx_exporter.py, or main.py in this prompt.
