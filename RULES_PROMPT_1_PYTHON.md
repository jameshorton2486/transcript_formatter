# DEPO TRANSCRIPT FORMATTER — PROMPT 1 OF 2: PYTHON RULES
# For: Codex
# Working directory: C:\Users\james\transcript_formatter\depo_formatter
# Touches: formatter.py, docx_exporter.py, main.py (dialog size only)
# Run PROMPT 1 (this file) first, then run PROMPT 2 (ai_tools rules).
# Stop on any failure. Verify after every step.

---

## ALREADY IMPLEMENTED — DO NOT TOUCH

These are already correct. Skip them entirely:
  ✓ normalize_dashes()       — em/en dash → --
  ✓ normalize_time_format()  — 10:14 AM → 10:14 a.m.
  ✓ normalize_reporter_label() — THE COURT REPORTER → THE REPORTER
  ✓ remove_filler_words()    — permanently disabled (verbatim preservation)
  ✓ fix_standalone_k()       — K. → Okay.
  ✓ fix_mhmm()               — Mhmm → Mm-hmm
  ✓ fix_leading_zero_time()  — 01:51 → 1:51
  ✓ fix_even_dollar_amounts() — $450.00 → $450
  ✓ fix_sentence_spacing()   — two spaces after . ?
  ✓ WRAP_WIDTH = 65
  ✓ US Letter page size, margins, font, line spacing, line numbers

---

## STEP 1 — ADD 6 NEW NORMALIZATION FUNCTIONS TO formatter.py

Open C:\Users\james\transcript_formatter\depo_formatter\formatter.py

Find the last normalization function in the file. It is:
```python
def fix_sentence_spacing(text: str) -> str:
```

After the end of fix_sentence_spacing(), add these 6 new functions:

```python
def fix_spaced_dashes(text: str) -> str:
    """
    Ensure exactly one space before and after every double-hyphen dash.
    Morson's requires: word -- word  (not word-- or --word or word--word).
    Works alongside normalize_dashes() which converts em/en dash first.
    """
    # Add spaces around -- where missing
    text = re.sub(r"(?<! )--(?! )", " -- ", text)
    # Collapse multiple spaces around -- to exactly one each side
    text = re.sub(r"\s+--\s+", " -- ", text)
    return text


def fix_uh_huh_hyphenation(text: str) -> str:
    """
    Normalize un-hyphenated affirmation/negation forms to hyphenated.
    Morson's requires: Uh-huh (affirmation), Uh-uh (negation) — strictly hyphenated.

    Deepgram sometimes outputs these without the hyphen:
      uh huh → Uh-huh
      uh uh  → Uh-uh
    """
    text = re.sub(r"\buh\s+huh\b", "Uh-huh", text, flags=re.IGNORECASE)
    text = re.sub(r"\buh\s+uh\b",  "Uh-uh",  text, flags=re.IGNORECASE)
    return text


def remove_duplicate_words(text: str) -> str:
    """
    Remove exact duplicate adjacent words that are 4 or more characters long.
    Deepgram artifact: "would would", "because because", "remember remember".

    SHORT words (1-3 chars) are deliberately kept:
      "I I", "so so", "the the" — may be intentional emphasis in speech.

    Examples:
      would would  → would
      because because → because
      I I think    → I I think   (unchanged — 'I' is 1 char)
      so so easy   → so so easy  (unchanged — 'so' is 2 chars)
    """
    return re.sub(r"\b(\w{4,})\s+\1\b", r"\1", text, flags=re.IGNORECASE)


def fix_doctor_artifact(text: str) -> str:
    """
    Deepgram sometimes inserts a period after 'Doctor' as if it were
    an abbreviation. Convert to Dr. before any proper noun corrections run.

    Examples:
      Doctor. Smith  → Dr. Smith
      Doctor. Garcia → Dr. Garcia
      the doctor was → the doctor was  (unchanged — no period, lowercase)
    """
    return re.sub(r"\bDoctor\.\s+(?=[A-Z])", "Dr. ", text)


def fix_percent_symbol(text: str) -> str:
    """
    Replace percent symbol with figures + spelled-out 'percent'.
    Morson's: use figures plus the word, never the % symbol.

    Examples:
      50%      → 50 percent
      8.5%     → 8.5 percent
      50 percent → 50 percent  (unchanged — already correct)
    """
    return re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", text)


def fix_okay_transition(text: str) -> str:
    """
    Convert transitional 'Okay,' and 'All right,' to end with a period,
    not a comma. Morson's: Q. Okay. Do you recall... (period, not comma).

    Applies to both Q. lines and A. lines wherever the pattern appears.

    Examples:
      Q.  Okay, do you recall   → Q.  Okay.  do you recall
      Q.  All right, now tell   → Q.  All right.  now tell
      A.  Okay, I understand.   → A.  Okay.  I understand.
    """
    return re.sub(
        r"\b(Okay|All right),\s+",
        r"\1.  ",
        text,
        flags=re.IGNORECASE,
    )
```

### 1b — Add all 6 calls to format_transcript()

Find the format_transcript() function. It currently ends with:
```python
    formatted = fix_sentence_spacing(formatted)
```

Add the 6 new calls immediately after that line:
```python
    formatted = fix_spaced_dashes(formatted)
    formatted = fix_uh_huh_hyphenation(formatted)
    formatted = remove_duplicate_words(formatted)
    formatted = fix_doctor_artifact(formatted)
    formatted = fix_percent_symbol(formatted)
    formatted = fix_okay_transition(formatted)
```

### 1c — Verify formatter.py

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\formatter.py" && Write-Host "PASS: formatter.py compiles" -ForegroundColor Green

python -c "
import sys; sys.path.insert(0, r'$app')
from formatter import (
    fix_spaced_dashes, fix_uh_huh_hyphenation, remove_duplicate_words,
    fix_doctor_artifact, fix_percent_symbol, fix_okay_transition,
    format_transcript
)
f = 0

def ck(label, got, exp):
    global f
    ok = got == exp
    print(f'  {chr(10003) if ok else chr(10007)} {label}')
    if not ok:
        print(f'    got:      {repr(got)}')
        print(f'    expected: {repr(exp)}')
        f += 1

ck('he--stopped',            fix_spaced_dashes('he--stopped'),             'he -- stopped')
ck('already spaced',         fix_spaced_dashes('he -- stopped'),            'he -- stopped')
ck('uh huh',                 fix_uh_huh_hyphenation('uh huh. Yes.'),        'Uh-huh. Yes.')
ck('uh uh',                  fix_uh_huh_hyphenation('uh uh. No.'),          'Uh-uh. No.')
ck('already hyphenated',     fix_uh_huh_hyphenation('Uh-huh.'),             'Uh-huh.')
ck('would would',            remove_duplicate_words('would would go'),       'would go')
ck('because because',        remove_duplicate_words('because because'),      'because')
ck('I I kept',               remove_duplicate_words('I I think'),            'I I think')
ck('so so kept',             remove_duplicate_words('so so easy'),           'so so easy')
ck('Doctor. Smith',          fix_doctor_artifact('Doctor. Smith'),           'Dr. Smith')
ck('lowercase kept',         fix_doctor_artifact('the doctor was'),         'the doctor was')
ck('50%',                    fix_percent_symbol('50%'),                      '50 percent')
ck('8.5%',                   fix_percent_symbol('8.5% interest'),            '8.5 percent interest')
ck('Okay, → Okay.',          fix_okay_transition('Q.  Okay, do you recall'), 'Q.  Okay.  do you recall')
ck('All right, → period',    fix_okay_transition('All right, now'),          'All right.  now')
ck('Okay. unchanged',        fix_okay_transition('Okay. Let us proceed.'),   'Okay. Let us proceed.')

print()
print(f'{15-f}/15 checks passed' if f == 0 else f'FAIL: {f} check(s) failed')
if f > 0:
    import sys; sys.exit(1)
"
```

---

## STEP 2 — UPDATE docx_exporter.py (5 TAB STOPS + STYLED RUNS)

Open C:\Users\james\transcript_formatter\depo_formatter\docx_exporter.py

### 2a — Replace the tab stop constants

Find:
```python
_TAB1     = 0.5              # Q./A. label
_TAB2     = 1.0              # text after Q./A.
_TAB3     = 1.5              # colloquy / parentheticals
```
Replace with:
```python
# UFM 5-stop tab system
_TAB1     = 0.25             # Q./A. labels           (360 twips)
_TAB2     = 0.625            # Q./A. text start       (900 twips)
_TAB3     = 1.0              # Speaker/Colloquy labels (1440 twips)
_TAB4     = 1.5              # Parentheticals          (2160 twips)
_TAB5     = 2.0              # Reserved               (2880 twips)

# Line type detection prefixes
_COLLOQUY_PREFIXES = ("MR.", "MS.", "MRS.", "DR.", "THE REPORTER:", "THE WITNESS:",
                      "THE INTERPRETER:", "THE COURT:", "COUNSEL:")
_PAREN_PREFIX      = "("
_FLAG_PREFIX       = "[SCOPIST:"
```

### 2b — Replace the _set_tab_stops call in _add_line()

Find in _add_line():
```python
    _set_tab_stops(para, [_TAB1, _TAB2, _TAB3])
```
Replace with:
```python
    _set_tab_stops(para, [_TAB1, _TAB2, _TAB3, _TAB4, _TAB5])
```

### 2c — Add run styling logic at the end of _add_line()

Find in _add_line():
```python
    content = f"{line_num:2d} {text}"
    run = para.add_run(content)
    run.font.name = _FONT
    run.font.size = _SIZE_PT
```
Replace with:
```python
    content = f"{line_num:2d} {text}"
    stripped = text.strip()

    run = para.add_run(content)
    run.font.name = _FONT
    run.font.size = _SIZE_PT

    # Speaker/Colloquy labels → bold, all-caps (the run already has the text)
    if any(stripped.upper().startswith(p) for p in _COLLOQUY_PREFIXES):
        run.bold = True

    # Parenthetical lines → navy blue
    elif stripped.startswith(_PAREN_PREFIX) and stripped.endswith(")"):
        from docx.shared import RGBColor
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x80)  # navy blue

    # Scopist flags → orange, bold
    elif stripped.startswith(_FLAG_PREFIX):
        from docx.shared import RGBColor
        run.font.color.rgb = RGBColor(0xFF, 0x80, 0x00)  # orange
        run.bold = True
        # Flags sit at full left margin — clear indent
        para.paragraph_format.left_indent = Inches(0)
        para.paragraph_format.first_line_indent = Inches(0)
```

### 2d — Verify docx_exporter.py

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\docx_exporter.py" && Write-Host "PASS: docx_exporter.py compiles" -ForegroundColor Green

python -c "
import sys, tempfile, os
sys.path.insert(0, r'$app')
from docx_exporter import export_to_docx, _TAB1, _TAB2, _TAB3, _TAB4, _TAB5
from docx import Document
from docx.shared import Inches

# Verify tab stop values
assert abs(_TAB1 - 0.25)  < 0.01, f'TAB1 wrong: {_TAB1}'
assert abs(_TAB2 - 0.625) < 0.01, f'TAB2 wrong: {_TAB2}'
assert abs(_TAB3 - 1.0)   < 0.01, f'TAB3 wrong: {_TAB3}'
assert abs(_TAB4 - 1.5)   < 0.01, f'TAB4 wrong: {_TAB4}'
assert abs(_TAB5 - 2.0)   < 0.01, f'TAB5 wrong: {_TAB5}'
print('PASS: 5 tab stops correct')

# Generate a test DOCX with all line types
sample = '''MR. DAVIS:  Did you review the documents?

A.  Yes, I did review them.

(The witness examined the exhibit.)

[SCOPIST: FLAG 1: Verify name spelling from audio]

Q.  What did you observe?'''

with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
    tmp = f.name

export_to_docx(sample, tmp)
doc = Document(tmp)
os.unlink(tmp)

# Check page geometry still correct
sec = doc.sections[0]
assert abs(sec.page_width  - Inches(8.5)) < 50, 'Page width wrong'
assert abs(sec.left_margin - Inches(1.5))  < 50, 'Left margin wrong'
print('PASS: page geometry preserved')

# Check bold on colloquy run
colloquy_paras = [p for p in doc.paragraphs if 'DAVIS' in p.text]
if colloquy_paras:
    bold_runs = [r for r in colloquy_paras[0].runs if r.bold]
    print(f'PASS: colloquy paragraph has bold run: {len(bold_runs) > 0}')

print('PASS: docx_exporter all checks passed')
"
```

---

## STEP 3 — UPDATE AI RESULT DIALOG SIZE IN main.py

The AI result dialog should match the preview panel dimensions so the
reviewer isn't squinting at a small window.

The main app window is 1280×820. The sidebar is 300px wide.
Preview panel = 980px wide × ~720px usable height.

Open C:\Users\james\transcript_formatter\depo_formatter\main.py

Find:
```python
        dialog.geometry("940x680")
```
Replace with:
```python
        dialog.geometry("980x740")
```

Also update the result_box font to match the preview textbox (currently FONT_MONO = Courier New 13pt):

Find:
```python
        result_box = ctk.CTkTextbox(
            dialog, wrap="word", font=FONT_MONO,
```
Replace with:
```python
        result_box = ctk.CTkTextbox(
            dialog, wrap="word", font=FONT_MONO,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
```

### Verify

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
python -m py_compile "$app\main.py" && Write-Host "PASS: main.py compiles" -ForegroundColor Green
Select-String -Path "$app\main.py" -Pattern "980x740" | Select-Object Line
```

---

## STEP 4 — FINAL INTEGRATION TEST

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"

foreach ($f in @("formatter.py","docx_exporter.py","main.py")) {
    python -m py_compile "$app\$f"
    if ($LASTEXITCODE -eq 0) { Write-Host "  PASS: $f" -ForegroundColor Green }
    else { Write-Host "  FAIL: $f" -ForegroundColor Red; exit 1 }
}

python -c "
import sys; sys.path.insert(0, r'$app')
from formatter import format_transcript

sample = '''THE COURT REPORTER:  It is 09:15 a.m.

MR. DAVIS:  Okay, let us begin. I would would like to ask you about the accident.

A.  uh huh. I remember. Doctor. Garcia told me my injury was about 25% healed.

Q.  All right, did you feel pain -- in your back?

would would you say it was severe?

(The witness examined Exhibit 1.)

[SCOPIST: FLAG 1: Verify spelling of name from audio]'''

result = format_transcript(sample)
print('--- OUTPUT ---')
print(result)
print()

checks = {
    'THE REPORTER normalized':        'THE REPORTER:' in result,
    'Spaced dashes':                  ' -- ' in result,
    'Uh huh → Uh-huh':               'Uh-huh' in result,
    'Duplicate would removed':        result.count('would') < result.count('would') + 1,
    'Doctor. → Dr.':                  'Dr. Garcia' in result,
    '25% → 25 percent':              '25 percent' in result,
    'Okay, → Okay.':                  'Okay.' in result and 'Okay,' not in result,
    'All right, → All right.':        'All right.' in result and 'All right,' not in result,
}
f = 0
for desc, ok in checks.items():
    print(f'  {chr(10003) if ok else chr(10007)} {desc}')
    if not ok: f += 1

print()
print('ALL INTEGRATION CHECKS PASSED' if f==0 else f'{f} FAILED')
if f > 0:
    import sys; sys.exit(1)
"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  PROMPT 1 COMPLETE — PYTHON RULES ADDED" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  formatter.py now handles:" -ForegroundColor White
Write-Host "    fix_spaced_dashes()        word--word → word -- word"
Write-Host "    fix_uh_huh_hyphenation()   uh huh → Uh-huh"
Write-Host "    remove_duplicate_words()   would would → would (4+ chars)"
Write-Host "    fix_doctor_artifact()      Doctor. Smith → Dr. Smith"
Write-Host "    fix_percent_symbol()       50% → 50 percent"
Write-Host "    fix_okay_transition()      Okay, → Okay."
Write-Host ""
Write-Host "  docx_exporter.py now has:" -ForegroundColor White
Write-Host "    5 UFM tab stops (0.25/0.625/1.0/1.5/2.0 inches)"
Write-Host "    Colloquy labels bold"
Write-Host "    Parentheticals navy blue"
Write-Host "    Scopist flags orange + bold"
Write-Host ""
Write-Host "  main.py:" -ForegroundColor White
Write-Host "    AI result dialog: 980x740 (matches preview panel)"
Write-Host ""
Write-Host "  >>> Run PROMPT 2 next for AI system prompt rules <<<"
Write-Host "======================================================" -ForegroundColor Cyan
```

---

## STOPPING CONDITIONS

Stop on any `py_compile` failure.
Stop if unit tests report failures.
Do NOT modify ai_tools.py, word_review.py, or file_loader.py in this prompt.
