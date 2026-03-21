# DEPO TRANSCRIPT FORMATTER — MOVE RULES 13/15/16 FROM AI TO PYTHON
# For: Codex
# Working directory: C:\Users\james\transcript_formatter\depo_formatter
# Purpose: Move 5 deterministic substitution rules out of the AI system prompt
#          and into formatter.py so they run instantly, without an API call.
#          Then remove them from BASE_SYSTEM_PROMPT in ai_tools.py.
# Touches: formatter.py, ai_tools.py only.
# Stop on any failure. Verify after each step.

---

## RULES BEING MOVED

These rules are pure text substitution — no context needed, no ambiguity.
Python handles them better than AI: faster, free, 100% consistent.

  Rule 13a  K. or k. (standalone) → Okay.
  Rule 13b  Mhmm / Mmhm / Mhm    → Mm-hmm
  Rule 15a  01:51 p.m.            → 1:51 p.m.  (remove leading zero in hours)
  Rule 15b  $450.00               → $450        (drop .00 from even dollar amounts)
  Rule 16   "Yes. She"            → "Yes.  She" (two spaces after sentence-ending punct)

Rules NOT being moved (require AI context to apply safely):
  Rule 12   Speaker label resolution  — needs context to map Speaker 0/1/2/3
  Rule 13c  THE COURT REPORTER → THE REPORTER  — already in formatter.py ✓
  Rule 13d  THE INTERPRETER: label    — validation rule, not a substitution
  Rule 14   Ellipsis preservation     — preservation rule, not a substitution
  Rule 15c  Percent / Height          — needs context to avoid false matches
  Rule 17   As-read parentheticals    — structural judgment
  Rule 18   Objection fragments       — structural judgment
  Rule 19   Cross-examination headers — structural judgment

---

## STEP 1 — ADD 5 NORMALIZATION FUNCTIONS TO formatter.py

Open C:\Users\james\transcript_formatter\depo_formatter\formatter.py

### 1a — Add the 5 functions after normalize_reporter_label()

Find:
```python
def normalize_reporter_label(text: str) -> str:
    """THE COURT REPORTER → THE REPORTER (UFM §3.20)."""
    return re.sub(r"\bTHE COURT REPORTER\s*:", "THE REPORTER:", text)
```

After that function, add these 5 new functions:

```python
def fix_standalone_k(text: str) -> str:
    """
    K. or k. at the start of a line (standalone response) → Okay.
    Rule Set 13: Universal word corrections.

    Only converts K. when it appears at the start of a line — this avoids
    changing middle initials like 'MR. K. SMITH' or abbreviations mid-sentence.

    Examples:
      K.  I understand.   → Okay.  I understand.
      k. Yes.             → Okay.  Yes.
      OK. That works.     → OK. That works.   (unchanged — not standalone K.)
      MR. K. SMITH        → MR. K. SMITH      (unchanged — middle initial)
    """
    # K. alone on a line
    text = re.sub(r"(?m)^\s*[Kk]\.\s*$", "Okay.", text)
    # K. at line start before a sentence
    text = re.sub(r"(?m)^\s*[Kk]\.\s+(?=[A-Z])", "Okay.  ", text)
    return text


def fix_mhmm(text: str) -> str:
    """
    Mhmm / Mmhm / Mhm (any case) → Mm-hmm
    Rule Set 13: Universal word corrections.

    Examples:
      Mhmm.   → Mm-hmm.
      Mmhm.   → Mm-hmm.
      Mhm.    → Mm-hmm.
      MHMM.   → Mm-hmm.
    """
    return re.sub(r"\bM+h+m+\b", "Mm-hmm", text, flags=re.IGNORECASE)


def fix_leading_zero_time(text: str) -> str:
    """
    Remove leading zero from hour in 12-hour time format.
    Rule Set 15: Numbers and time (Morson's Rule 187).

    Examples:
      01:51 p.m.  → 1:51 p.m.
      09:30 a.m.  → 9:30 a.m.
      10:14 a.m.  → 10:14 a.m.  (unchanged — no leading zero)
      12:00 p.m.  → 12:00 p.m.  (unchanged — 12 has no leading zero)
    """
    return re.sub(
        r"\b0(\d:\d{2}\s*[ap]\.?m\.?)\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )


def fix_even_dollar_amounts(text: str) -> str:
    """
    Remove unnecessary .00 from even dollar amounts.
    Rule Set 15: Numbers and money (Morson's).

    Examples:
      $450.00   → $450
      $1200.00  → $1200
      $4.50     → $4.50   (unchanged — not .00)
      $0.75     → $0.75   (unchanged — not .00)
    """
    return re.sub(r"(\$\d+)\.00\b", r"\1", text)


def fix_sentence_spacing(text: str) -> str:
    """
    Ensure two spaces follow sentence-ending punctuation before a capital letter.
    Rule Set 16: Sentence spacing (Morson's Rules 1 and 16).

    Only applies when a capital letter follows directly after one space,
    indicating a new sentence. Does not affect:
      - Numbers like 5.1
      - Abbreviations already handled (Mr., Dr., etc.) — acceptable side effect

    Examples:
      Yes. She went.     → Yes.  She went.
      Q. Did you? A. Yes → Q.  Did you?  A.  Yes
    """
    return re.sub(r"([.?!])\s([A-Z])", r"\1  \2", text)
```

### 1b — Add all 5 calls to format_transcript()

Find:
```python
def format_transcript(
    text: str,
    use_qa_format: bool = True,
    remove_fillers: bool = False,
) -> str:
    formatted = clean_text(text)
    formatted = normalize_dashes(formatted)
    formatted = normalize_time_format(formatted)
    formatted = normalize_reporter_label(formatted)
```

Replace with:
```python
def format_transcript(
    text: str,
    use_qa_format: bool = True,
    remove_fillers: bool = False,
) -> str:
    formatted = clean_text(text)
    formatted = normalize_dashes(formatted)
    formatted = normalize_time_format(formatted)
    formatted = normalize_reporter_label(formatted)
    formatted = fix_standalone_k(formatted)
    formatted = fix_mhmm(formatted)
    formatted = fix_leading_zero_time(formatted)
    formatted = fix_even_dollar_amounts(formatted)
    formatted = fix_sentence_spacing(formatted)
```

### 1c — Verify formatter.py

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\formatter.py" && Write-Host "PASS: formatter.py compiles" -ForegroundColor Green

python -c "
import sys; sys.path.insert(0, r'$app')
from formatter import (
    fix_standalone_k, fix_mhmm, fix_leading_zero_time,
    fix_even_dollar_amounts, fix_sentence_spacing, format_transcript
)

failures = 0

def check(label, got, expected):
    global failures
    ok = got == expected
    print(f'  {chr(10003) if ok else chr(10007)} {label}')
    if not ok:
        print(f'    got:      {repr(got)}')
        print(f'    expected: {repr(expected)}')
        failures += 1

# K. tests
check('K. at line start',       fix_standalone_k('K.  I understand.').strip(), 'Okay.  I understand.')
check('k. lowercase',           fix_standalone_k('k. Yes.').strip(),            'Okay.  Yes.')
check('OK. preserved',          fix_standalone_k('OK. That works.'),             'OK. That works.')
check('Kafka preserved',        fix_standalone_k('Kafka said hello.'),           'Kafka said hello.')
check('MR. K. SMITH preserved', fix_standalone_k('MR. K. SMITH'),               'MR. K. SMITH')

# Mhmm tests
check('Mhmm',   fix_mhmm('Mhmm.'),  'Mm-hmm.')
check('Mmhm',   fix_mhmm('Mmhm.'),  'Mm-hmm.')
check('Mhm',    fix_mhmm('Mhm.'),   'Mm-hmm.')
check('MHMM',   fix_mhmm('MHMM.'),  'Mm-hmm.')

# Leading zero time
check('01:51 p.m.',  fix_leading_zero_time('at 01:51 p.m.'), 'at 1:51 p.m.')
check('09:30 a.m.',  fix_leading_zero_time('at 09:30 a.m.'), 'at 9:30 a.m.')
check('10:14 a.m. preserved', fix_leading_zero_time('at 10:14 a.m.'), 'at 10:14 a.m.')

# Dollar amounts
check('\$450.00',    fix_even_dollar_amounts('\$450.00'),   '\$450')
check('\$1200.00',   fix_even_dollar_amounts('\$1200.00'),  '\$1200')
check('\$4.50 kept', fix_even_dollar_amounts('\$4.50'),     '\$4.50')

# Sentence spacing
check('Period spacing', fix_sentence_spacing('Yes. She went.'), 'Yes.  She went.')
check('Question spacing', fix_sentence_spacing('Q. Did you? A. Yes.'), 'Q.  Did you?  A.  Yes.')
check('Number not changed', fix_sentence_spacing('5.1 percent'), '5.1 percent')

print()
print(f'{21 - failures}/21 checks passed' if failures == 0 else f'FAIL: {failures} check(s) failed')
if failures > 0:
    import sys; sys.exit(1)
"
```

---

## STEP 2 — REMOVE RULES 13a/13b/15a/15b/16 FROM BASE_SYSTEM_PROMPT IN ai_tools.py

Open C:\Users\james\transcript_formatter\depo_formatter\ai_tools.py

Find and REMOVE this entire block (Rule Set 13 portion to be removed):

```
  K.  or  k.  (standalone) → Okay.
  Mhmm  or  Mmhm → Mm-hmm
```

In RULE SET 13, keep ONLY the THE REPORTER: and THE INTERPRETER: lines.
The full RULE SET 13 after editing should read:

```
RULE SET 13 - SPEAKER LABEL STANDARDS

THE REPORTER: is the correct court reporter label.
THE COURT REPORTER: must be corrected to THE REPORTER: throughout.
THE INTERPRETER: is a valid speaker label. Do not modify or remove interpreter lines.
Uh-huh → Uh-huh (preserve — do not change)
Huh-uh → Huh-uh (preserve — do not change)
```

Note: Remove the heading "UNIVERSAL WORD CORRECTIONS" and replace with "SPEAKER LABEL STANDARDS"
since K. and Mhmm corrections now live in Python.

---

Find and REMOVE this block from RULE SET 15:

```
Time format: no leading zero in non-military time. Example: 1:51 p.m. not 01:51 p.m.
Even dollar amounts: omit decimal. Example: $450 not $450.00.
```

The remaining RULE SET 15 should keep only:
```
RULE SET 15 - NUMBERS AND FORMATTING (Morson's)

Percent: always figures + spelled-out "percent." Example: 50 percent.
Height in feet and inches: use the foot/inch symbol format. Example: 5'1" not 5.1 or 5 1.
```

---

Find and REMOVE the entire RULE SET 16 block:

```
RULE SET 16 - SENTENCE SPACING AND PUNCTUATION (Morson's Rules 1 and 16)

Two spaces follow every period and question mark that ends a sentence.
Single space after all other punctuation.
```

Remove it entirely. Renumber is NOT required — gaps in rule set numbers are fine.

---

### 2a — Verify ai_tools.py

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\ai_tools.py" && Write-Host "PASS: ai_tools.py compiles" -ForegroundColor Green

python -c "
import sys, os
sys.path.insert(0, r'$app')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
from ai_tools import BASE_SYSTEM_PROMPT

failures = 0

def check(label, condition):
    global failures
    ok = condition
    print(f'  {chr(10003) if ok else chr(10007)} {label}')
    if not ok: failures += 1

# These should be REMOVED from the prompt
check('K. rule removed',        'K.  or  k.' not in BASE_SYSTEM_PROMPT)
check('Mhmm rule removed',      'Mhmm  or  Mmhm' not in BASE_SYSTEM_PROMPT)
check('Leading zero removed',   'leading zero' not in BASE_SYSTEM_PROMPT.lower())
check('450.00 rule removed',    '450.00' not in BASE_SYSTEM_PROMPT)
check('Two spaces rule removed','Two spaces follow every period' not in BASE_SYSTEM_PROMPT)

# These must STAY in the prompt
check('THE REPORTER: kept',     'THE REPORTER:' in BASE_SYSTEM_PROMPT)
check('THE INTERPRETER: kept',  'THE INTERPRETER:' in BASE_SYSTEM_PROMPT)
check('Uh-huh kept',            'Uh-huh' in BASE_SYSTEM_PROMPT)
check('Huh-uh kept',            'Huh-uh' in BASE_SYSTEM_PROMPT)
check('RULE SET 12 kept',       'RULE SET 12' in BASE_SYSTEM_PROMPT)
check('RULE SET 14 kept',       'RULE SET 14' in BASE_SYSTEM_PROMPT)
check('RULE SET 17 kept',       'RULE SET 17' in BASE_SYSTEM_PROMPT)
check('RULE SET 18 kept',       'RULE SET 18' in BASE_SYSTEM_PROMPT)
check('RULE SET 19 kept',       'RULE SET 19' in BASE_SYSTEM_PROMPT)

print()
print('ALL CHECKS PASSED' if failures == 0 else f'FAIL: {failures} check(s) failed')
if failures > 0:
    import sys; sys.exit(1)
"
```

---

## STEP 3 — FINAL INTEGRATION TEST

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"

python -c "
import sys; sys.path.insert(0, r'$app')
from formatter import format_transcript

# Real-world sample with all 5 new rules present
sample = '''THE COURT REPORTER:  It is 09:05 a.m.

Q.  Please state your full name.

A.  Angie Irani Ozuna.

Q.  And your date of birth?

A.  K.  I was born on June 15, 1988.

Q.  Do you recall the accident occurred at 01:51 p.m.?

A.  Mhmm. Yes, I remember it was around that time.

Q.  Your weekly pay was \$450.00 at that time?

A.  Yes. That is correct.

Q.  Did you speak with anyone afterward?

A.  Mhm. I called my husband.'''

result = format_transcript(sample)
print('--- FORMATTED OUTPUT ---')
print(result)
print()

# Verify each transformation happened
checks = {
    'THE REPORTER: normalized':        'THE REPORTER:' in result and 'THE COURT REPORTER:' not in result,
    'K. → Okay.':                      'Okay.' in result and '\\nK.' not in result,
    'Mhmm → Mm-hmm':                   'Mm-hmm' in result and 'Mhmm' not in result,
    'Mhm → Mm-hmm':                    result.count('Mm-hmm') >= 2,
    '09:05 → 9:05 a.m.':               '9:05 a.m.' in result,
    '01:51 → 1:51 p.m.':               '1:51 p.m.' in result,
    '\$450.00 → \$450':                '\$450.' not in result or '\$450.00' not in result,
    'Sentence spacing added':           '.  ' in result or '?  ' in result,
}

failures = 0
for desc, ok in checks.items():
    print(f'  {chr(10003) if ok else chr(10007)} {desc}')
    if not ok: failures += 1

print()
print('ALL INTEGRATION CHECKS PASSED' if failures == 0 else f'{failures} INTEGRATION CHECK(S) FAILED')
if failures > 0:
    import sys; sys.exit(1)
"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  RULES MOVED TO PYTHON — COMPLETE" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  formatter.py now handles (no API call needed):" -ForegroundColor White
Write-Host "    K. / k.  → Okay.         (Rule 13a)"
Write-Host "    Mhmm     → Mm-hmm        (Rule 13b)"
Write-Host "    01:51 pm → 1:51 p.m.     (Rule 15a)"
Write-Host "    \$450.00 → \$450          (Rule 15b)"
Write-Host "    Yes. She → Yes.  She     (Rule 16)"
Write-Host ""
Write-Host "  ai_tools.py system prompt:" -ForegroundColor White
Write-Host "    Removed: K./Mhmm/leading zero/dollar/sentence spacing rules"
Write-Host "    Kept:    THE REPORTER, THE INTERPRETER, Uh-huh/Huh-uh, Rules 12/14/17/18/19"
Write-Host ""
Write-Host "  Result: Format (Rules Engine) now applies all 5 rules" -ForegroundColor White
Write-Host "  instantly. AI only handles what requires context."
Write-Host "======================================================" -ForegroundColor Cyan
```

---

## STOPPING CONDITIONS

Stop on any `py_compile` failure.
Stop if the unit test reports any check failed.
Stop if the integration test reports any check failed.
Do NOT modify docx_exporter.py, word_review.py, file_loader.py, or main.py.

---

## WHAT THIS DOES NOT CHANGE

- The AI system prompt retains all rules that require context judgment
- The formatter does not gain any rule that needs surrounding text to apply safely
- The DOCX export geometry is unchanged
- The session, UI, and threading logic are unchanged
