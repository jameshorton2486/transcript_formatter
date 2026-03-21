# DEPO TRANSCRIPT FORMATTER  DEPLOY FIXES, REMOVE COZY-CORNER, FULL AUDIT
# For: Codex (OpenAI) or Claude Code
# Run from: C:\Users\james\  (your Windows home directory)
# This prompt is safe to re-run. Every step checks before acting.
# cozy-corner will be DELETED by this prompt. Read Step 2 before running.

---

## CONTEXT

You are maintaining a Windows 11 Python desktop application called
"Depo Transcript Formatter". The application lives at:

  C:\Users\james\transcript_formatter\depo_formatter\

Six fixed Python files and one updated requirements.txt are sitting in
the Downloads folder:

  C:\Users\james\Downloads\ai_tools.py
  C:\Users\james\Downloads\word_review.py
  C:\Users\james\Downloads\formatter.py
  C:\Users\james\Downloads\docx_exporter.py
  C:\Users\james\Downloads\main.py
  C:\Users\james\Downloads\requirements.txt

The repo root also contains an unrelated folder called cozy-corner that
must be removed. It is a children's music studio project that was
accidentally zipped into the same archive. It has zero connection to
the transcript formatter.

---

## MANDATORY BOUNDARY LOG

At the start of your session, print:
```
[DEPO-FORMATTER-DEPLOY] Session start
[DEPO-FORMATTER-DEPLOY] App path: C:\Users\james\transcript_formatter\depo_formatter
[DEPO-FORMATTER-DEPLOY] Task: deploy 6 fixed files + remove cozy-corner + full audit
```

At the end of every step, print:
```
[DEPO-FORMATTER-DEPLOY] Step N complete  PASS / FAIL
```

---

## STEP 1  VERIFY SOURCE FILES EXIST IN DOWNLOADS

Before copying anything, confirm every source file is present:

```powershell
$downloads = "$env:USERPROFILE\Downloads"
$files = @("ai_tools.py","word_review.py","formatter.py","docx_exporter.py","main.py","requirements.txt")
$missing = @()
foreach ($f in $files) {
    $path = Join-Path $downloads $f
    if (Test-Path $path) {
        Write-Host "  FOUND: $f" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $f" -ForegroundColor Red
        $missing += $f
    }
}
if ($missing.Count -gt 0) {
    Write-Error "Cannot proceed. Missing files in Downloads: $($missing -join ', ')"
    exit 1
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 1 complete  PASS" -ForegroundColor Cyan
```

If any file is missing, STOP and report which files are missing.
Do NOT proceed to Step 2.

---

## STEP 2  BACKUP CURRENT FILES

Before overwriting anything, back up the current versions.
This lets you restore if something goes wrong.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
$backup = "C:\Users\james\transcript_formatter\depo_formatter_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

if (-not (Test-Path $app)) {
    Write-Error "App directory not found: $app"
    exit 1
}

Copy-Item -Path $app -Destination $backup -Recurse -Force
Write-Host "  Backup created: $backup" -ForegroundColor Green
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 2 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 3  COPY FIXED FILES INTO THE APP

Copy all 6 files from Downloads to the app directory, replacing the originals.

```powershell
$downloads = "$env:USERPROFILE\Downloads"
$app = "C:\Users\james\transcript_formatter\depo_formatter"
$files = @("ai_tools.py","word_review.py","formatter.py","docx_exporter.py","main.py","requirements.txt")

foreach ($f in $files) {
    $src  = Join-Path $downloads $f
    $dest = Join-Path $app $f
    Copy-Item -Path $src -Destination $dest -Force
    Write-Host "  COPIED: $f" -ForegroundColor Green
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 3 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 4  REMOVE cozy-corner

**What this deletes:** C:\Users\james\transcript_formatter\cozy-corner\
This is a children's music studio project (Sunny's Learning World /
Cozy Club). It is NOT part of the transcript formatter. It has zero
Python imports, zero references, and zero shared code with the
formatter app. Deleting it does NOT affect the formatter in any way.

**What this does NOT delete:** The transcript formatter app at
C:\Users\james\transcript_formatter\depo_formatter\ is untouched.

```powershell
$cozycorner = "C:\Users\james\transcript_formatter\cozy-corner"

if (Test-Path $cozycorner) {
    Remove-Item -Path $cozycorner -Recurse -Force
    Write-Host "  DELETED: cozy-corner" -ForegroundColor Green
} else {
    Write-Host "  cozy-corner not found  already removed or path is different" -ForegroundColor Yellow
    # Check parent directory for any cozy-corner variant
    Get-ChildItem "C:\Users\james\transcript_formatter" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*cozy*" } |
        ForEach-Object { Write-Host "  Found possible cozy folder: $($_.FullName)" -ForegroundColor Yellow }
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 4 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 5  INSTALL UPDATED DEPENDENCIES

The new requirements.txt adds the `anthropic` SDK and makes `pywin32`
Windows-conditional. Run pip install inside the existing venv.

```powershell
$app  = "C:\Users\james\transcript_formatter\depo_formatter"
$venv = "$app\.venv\Scripts\Activate.ps1"

if (Test-Path $venv) {
    & $venv
    pip install -r "$app\requirements.txt" --upgrade --quiet
    Write-Host "  Dependencies installed via venv" -ForegroundColor Green
} else {
    Write-Host "  No venv found  installing to system Python" -ForegroundColor Yellow
    pip install -r "$app\requirements.txt" --upgrade --quiet
}

# Confirm anthropic SDK is now available
python -c "import anthropic; print('  anthropic SDK version:', anthropic.__version__)"
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 5 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 6  SYNTAX VERIFICATION (ALL PYTHON FILES)

Parse every .py file in the app directory with Python's AST parser.
Any syntax error will be caught here before the app tries to run.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
$py_files = Get-ChildItem -Path $app -Filter "*.py" | Select-Object -ExpandProperty FullName
$errors = 0

foreach ($pyfile in $py_files) {
    $result = python -c "
import ast, sys
try:
    ast.parse(open(r'$pyfile', encoding='utf-8').read())
    print('  OK:', r'$pyfile'.split('\\')[-1])
except SyntaxError as e:
    print('  FAIL:', r'$pyfile'.split('\\')[-1], '-', str(e))
    sys.exit(1)
"
    Write-Host $result
    if ($LASTEXITCODE -ne 0) { $errors++ }
}

if ($errors -gt 0) {
    Write-Error "$errors file(s) have syntax errors. Do not run the app."
    exit 1
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 6 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 7  CONTENT AUDIT: VERIFY ALL FIXES ARE APPLIED

Check that each specific fix is present in the deployed files.
If any check fails, report exactly what is wrong.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
$failures = 0

function Check-File {
    param($file, $desc, $pattern, $shouldMatch=$true)
    $path = Join-Path $app $file
    $content = Get-Content $path -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        Write-Host "  FAIL  [$file] Cannot read file" -ForegroundColor Red
        $script:failures++
        return
    }
    $found = $content -match [regex]::Escape($pattern)
    if ($shouldMatch -and $found) {
        Write-Host "  PASS  [$file] $desc" -ForegroundColor Green
    } elseif (-not $shouldMatch -and -not $found) {
        Write-Host "  PASS  [$file] $desc" -ForegroundColor Green
    } else {
        $action = if ($shouldMatch) { "NOT FOUND in" } else { "STILL PRESENT in" }
        Write-Host "  FAIL  [$file] $desc  '$pattern' $action file" -ForegroundColor Red
        $script:failures++
    }
}

# formatter.py fixes
Check-File "formatter.py" "WRAP_WIDTH = 65 (UFM 2.5)"         "WRAP_WIDTH = 65"
Check-File "formatter.py" "WRAP_WIDTH not 72 (old wrong value)" "WRAP_WIDTH = 72"           -shouldMatch:$false
Check-File "formatter.py" "Continuation indent = empty (UFM 2.10)" 'CONTINUATION_INDENT = ""'
Check-File "formatter.py" "normalize_dashes function present"   "def normalize_dashes"
Check-File "formatter.py" "normalize_time_format present"       "def normalize_time_format"
Check-File "formatter.py" "normalize_reporter_label present"    "def normalize_reporter_label"

# docx_exporter.py fixes
Check-File "docx_exporter.py" "US Letter width set"             "Inches(8.5)"
Check-File "docx_exporter.py" "US Letter height set"            "Inches(11)"
Check-File "docx_exporter.py" "Left margin 1.5 inch"            "Inches(1.5)"
Check-File "docx_exporter.py" "Right margin 0.5 inch"           "Inches(0.5)"
Check-File "docx_exporter.py" "28pt line spacing"               "Pt(28)"
Check-File "docx_exporter.py" "Explicit tab stops"              "_set_tab_stops"
Check-File "docx_exporter.py" "Format box border function"      "_apply_box_border"
Check-File "docx_exporter.py" "25 lines per page constant"      "_LINES_PG = 25"

# ai_tools.py fixes
Check-File "ai_tools.py" "Uses anthropic SDK"                   "import anthropic"
Check-File "ai_tools.py" "Correct model: claude-sonnet-4-6"    "claude-sonnet-4-6"

# AST-aware check: only fails if invalid model is in executable code, not a comment
$astCheck = python -c "
import ast, sys
src = open(r'$app\ai_tools.py', encoding='utf-8').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'MODEL_CANDIDATES':
                vals = [elt.value for elt in node.value.elts if hasattr(elt, 'value')]
                bad = [v for v in vals if '20250514' in v]
                if bad:
                    print('FAIL')
                    sys.exit(1)
                else:
                    print('PASS')
" 2>&1
if ($astCheck -eq "PASS") {
    Write-Host "  PASS  [ai_tools.py] Invalid model ID not in active MODEL_CANDIDATES list" -ForegroundColor Green
} else {
    Write-Host "  FAIL  [ai_tools.py] Invalid model ID still in MODEL_CANDIDATES  fix required" -ForegroundColor Red
    $script:failures++
}

Check-File "ai_tools.py" "requests library removed"            "import requests"           -shouldMatch:$false
Check-File "ai_tools.py" "max_tokens raised to 8000"           "max_tokens: int = 8000"
Check-File "ai_tools.py" "120 second timeout"                  "timeout=120"

# word_review.py fixes
Check-File "word_review.py" "Lazy win32 import (not at module top)"  "import win32com.client"
Check-File "word_review.py" "Windows platform guard function"         "_require_windows"
Check-File "word_review.py" "platform.system check"                   "platform.system()"
Check-File "word_review.py" "win32 not imported at module level" "^import win32com" -shouldMatch:$false

# main.py fixes
Check-File "main.py" "Threading used for AI calls"              "threading.Thread"
Check-File "main.py" "Progress bar present"                     "CTkProgressBar"
Check-File "main.py" "Two-panel layout (sidebar)"               "_build_sidebar"
Check-File "main.py" "Two-panel layout (preview)"               "_build_preview_panel"
Check-File "main.py" "PII removed: Enrique Benavides"           "Enrique Benavides"  -shouldMatch:$false
Check-File "main.py" "PII removed: Gerardo Alba"                "Gerardo Alba"        -shouldMatch:$false
Check-File "main.py" "PII removed: Luciano Hernandez"           "Luciano Hernandez"   -shouldMatch:$false

# requirements.txt
Check-File "requirements.txt" "anthropic SDK listed"            "anthropic"

Write-Host ""
if ($failures -eq 0) {
    Write-Host "  ALL CHECKS PASSED ($( (Get-Item "$app\*.py").Count ) files verified)" -ForegroundColor Cyan
} else {
    Write-Host "  $failures CHECK(S) FAILED  do not run the app until fixed" -ForegroundColor Red
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 7 complete  $( if ($failures -eq 0) { 'PASS' } else { 'FAIL' } )" -ForegroundColor Cyan
```

---

## STEP 8  IMPORT VERIFICATION (ALL MODULES)

Test that all modules import without errors. This catches missing
dependencies and broken import chains before the app launches.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"

$imports = @(
    "from app_logging import get_logger",
    "from file_loader import load_file",
    "from formatter import format_transcript",
    "from docx_exporter import export_to_docx"
)

Push-Location $app
$errors = 0

foreach ($imp in $imports) {
    $result = python -c "$imp; print('  OK: $imp')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host $result -ForegroundColor Green
    } else {
        Write-Host "  FAIL: $imp" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        $errors++
    }
}

# Test ai_tools import separately  it loads dotenv/anthropic
$result = python -c "
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key-for-import-check')
from ai_tools import BASE_SYSTEM_PROMPT, MODEL_CANDIDATES, VALID_DASH_STYLES
print('  OK: ai_tools (model 0:', MODEL_CANDIDATES[0] + ')')
" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $result -ForegroundColor Green
} else {
    Write-Host "  FAIL: ai_tools" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    $errors++
}

# Test word_review import  should succeed even on Windows without Word installed
$result = python -c "
from word_review import derive_review_output_path, normalize_lines, is_protected_line
print('  OK: word_review (lazy win32 import confirmed)')
" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host $result -ForegroundColor Green
} else {
    Write-Host "  FAIL: word_review" -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    $errors++
}

Pop-Location

if ($errors -gt 0) {
    Write-Error "$errors import(s) failed. Run: pip install -r requirements.txt"
    exit 1
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 8 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 9  UNIT TESTS: FORMATTER AND DOCX EXPORTER

Run targeted tests against the two most-changed logic files to verify
UFM compliance without needing to launch the full GUI.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"
Push-Location $app

python -c "
import sys
sys.path.insert(0, '.')
from formatter import WRAP_WIDTH, CONTINUATION_INDENT, format_transcript, normalize_dashes, normalize_time_format, normalize_reporter_label

failures = 0

def check(desc, actual, expected):
    global failures
    ok = actual == expected
    print(f'  {chr(10003) if ok else chr(10007)} {desc}')
    if not ok:
        print(f'    got:      {repr(actual)}')
        print(f'    expected: {repr(expected)}')
        failures += 1

# UFM geometry constants
check('WRAP_WIDTH is 65',        WRAP_WIDTH,           65)
check('CONTINUATION_INDENT is empty', CONTINUATION_INDENT, '')

# dash normalization
check('em dash -> double hyphen',   normalize_dashes('he -- stopped\u2014abruptly'), 'he -- stopped -- abruptly')
check('en dash -> double hyphen',   normalize_dashes('Q.\u2013A.'), 'Q. -- A.')

# time normalization
check('AM uppercase -> a.m.',       normalize_time_format('at 10:14 AM'), 'at 10:14 a.m.')
check('PM lowercase -> p.m.',       normalize_time_format('at 2:35 pm'),  'at 2:35 p.m.')
check('already correct unchanged',  normalize_time_format('at 2:35 p.m.'), 'at 2:35 p.m.')

# reporter label
check('THE COURT REPORTER -> THE REPORTER:', normalize_reporter_label('THE COURT REPORTER: It is'), 'THE REPORTER: It is')
check('THE REPORTER: unchanged',             normalize_reporter_label('THE REPORTER: It is'),       'THE REPORTER: It is')

print()
print(f'  Formatter tests: {9-failures}/9 passed')
if failures > 0:
    print(f'  {failures} FAILURE(S)  formatter.py not correctly fixed')
    sys.exit(1)
"

$fmt_ok = $LASTEXITCODE -eq 0

python -c "
import sys, os, tempfile
sys.path.insert(0, '.')
from docx_exporter import export_to_docx
from docx import Document
from docx.shared import Inches

failures = 0

def check(desc, actual, expected, tol=50):
    global failures
    ok = abs(actual - expected) <= tol
    print(f'  {chr(10003) if ok else chr(10007)} {desc}: {actual} (expected {expected})')
    if not ok:
        failures += 1

# Generate a test DOCX
sample = '\n'.join([f'Q.  Question number {i}.' if i%2==0 else f'A.  Answer number {i}.' for i in range(1,26)])
with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
    tmp = f.name

export_to_docx(sample, tmp)
doc = Document(tmp)
sec = doc.sections[0]
os.unlink(tmp)

check('Page width  = 8.5 inch', sec.page_width,    Inches(8.5))
check('Page height = 11 inch',  sec.page_height,   Inches(11))
check('Left margin = 1.5 inch', sec.left_margin,   Inches(1.5))
check('Right margin = 0.5 inch',sec.right_margin,  Inches(0.5))
check('Top margin = 0.75 inch', sec.top_margin,    Inches(0.75))
check('Bottom margin = 0.75 in',sec.bottom_margin, Inches(0.75))

# Check line spacing on first body paragraph
body_paras = [p for p in doc.paragraphs if p.text.strip()]
if body_paras:
    sp = body_paras[0].paragraph_format.line_spacing
    ok = sp is not None and abs(sp.pt - 28.0) < 0.5
    print(f'  {chr(10003) if ok else chr(10007)} Line spacing = exactly 28pt: {sp.pt if sp else None}')
    if not ok: failures += 1

print()
print(f'  Exporter tests: {7-failures}/7 passed')
if failures > 0:
    print(f'  {failures} FAILURE(S)  docx_exporter.py not correctly fixed')
    sys.exit(1)
"

$exp_ok = $LASTEXITCODE -eq 0
Pop-Location

if (-not $fmt_ok -or -not $exp_ok) {
    Write-Error "Unit tests failed. Do not run the app."
    exit 1
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 9 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 10  COZY-CORNER CONFIRMED DELETED

Verify cozy-corner is gone and the formatter files are intact.

```powershell
$cozycorner = "C:\Users\james\transcript_formatter\cozy-corner"
$app = "C:\Users\james\transcript_formatter\depo_formatter"

if (Test-Path $cozycorner) {
    Write-Host "  FAIL: cozy-corner still exists at $cozycorner" -ForegroundColor Red
    Write-Host "  Run Step 4 again to remove it." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  PASS: cozy-corner deleted" -ForegroundColor Green
}

# Confirm formatter app is still intact
$required = @("main.py","ai_tools.py","formatter.py","docx_exporter.py","word_review.py","requirements.txt","app_logging.py","file_loader.py")
$intact = $true
foreach ($f in $required) {
    $path = Join-Path $app $f
    if (Test-Path $path) {
        Write-Host "  INTACT: $f" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $f" -ForegroundColor Red
        $intact = $false
    }
}

if (-not $intact) {
    Write-Error "Formatter app files are missing. Restore from backup."
    exit 1
}
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 10 complete  PASS" -ForegroundColor Cyan
```

---

## STEP 11  FINAL AUDIT REPORT

Print a complete human-readable summary of the application state.

```powershell
$app = "C:\Users\james\transcript_formatter\depo_formatter"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  DEPO TRANSCRIPT FORMATTER  FINAL AUDIT REPORT" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "  App location: $app"
Write-Host ""

Write-Host "  File inventory:" -ForegroundColor White
Get-ChildItem $app -Filter "*.py" | ForEach-Object {
    $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
    Write-Host "    $($_.Name.PadRight(22)) $lines lines"
}

Write-Host ""
Write-Host "  Python version:"
python --version

Write-Host ""
Write-Host "  Installed packages (key dependencies):"
$pkgs = @("customtkinter","python-docx","pdfplumber","anthropic","python-dotenv","pywin32")
foreach ($pkg in $pkgs) {
    $ver = pip show $pkg 2>$null | Select-String "^Version:" | ForEach-Object { $_ -replace "Version: ","" }
    if ($ver) {
        Write-Host "    $($pkg.PadRight(18)) $ver" -ForegroundColor Green
    } else {
        Write-Host "    $($pkg.PadRight(18)) NOT INSTALLED" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "  Critical fixes confirmed:"
$checks = @(
    @{ file="formatter.py";     key="WRAP_WIDTH = 65";           desc="Wrap width = 65 (UFM 2.5)" },
    @{ file="docx_exporter.py"; key="Inches(8.5)";               desc="US Letter page size" },
    @{ file="docx_exporter.py"; key="Pt(28)";                    desc="28pt line spacing" },
    @{ file="ai_tools.py";      key="import anthropic";           desc="anthropic SDK (not requests)" },
    @{ file="ai_tools.py";      key="claude-sonnet-4-6";         desc="Correct model ID" },
    @{ file="word_review.py";   key="_require_windows";           desc="Windows-only guard (no crash on macOS)" },
    @{ file="main.py";          key="threading.Thread";           desc="AI calls on background thread" }
)
foreach ($c in $checks) {
    $content = Get-Content (Join-Path $app $c.file) -Raw
    $found = $content -match [regex]::Escape($c.key)
    $status = if ($found) { "OK" } else { "MISSING" }
    $color  = if ($found) { "Green" } else { "Red" }
    Write-Host "    [$status] $($c.desc)" -ForegroundColor $color
}

Write-Host ""
Write-Host "  cozy-corner status:"
$cozycorner = "C:\Users\james\transcript_formatter\cozy-corner"
if (Test-Path $cozycorner) {
    Write-Host "    [EXISTS] cozy-corner still present  run Step 4" -ForegroundColor Red
} else {
    Write-Host "    [DELETED] cozy-corner removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "  .env file:"
$env_path = Join-Path $app ".env"
if (Test-Path $env_path) {
    $has_key = (Get-Content $env_path -Raw) -match "ANTHROPIC_API_KEY\s*=\s*\S+"
    if ($has_key) {
        Write-Host "    [SET] ANTHROPIC_API_KEY is configured" -ForegroundColor Green
    } else {
        Write-Host "    [EMPTY] .env exists but ANTHROPIC_API_KEY is not set" -ForegroundColor Yellow
    }
} else {
    Write-Host "    [MISSING] .env file not found  AI features will not work" -ForegroundColor Yellow
    Write-Host "    Create it: echo ANTHROPIC_API_KEY=your-key > $env_path"
}

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "[DEPO-FORMATTER-DEPLOY] Step 11 complete  PASS" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NEXT STEPS:" -ForegroundColor White
Write-Host "  1. If all checks above show OK (green), launch the app:"
Write-Host "       cd $app"
Write-Host "       .\.venv\Scripts\Activate.ps1"
Write-Host "       python main.py"
Write-Host "  2. Upload a real transcript file (.txt, .docx, or .pdf)"
Write-Host "  3. Click 'Format (Rules Engine)'  verify the transcript wraps at ~65 chars"
Write-Host "  4. If ANTHROPIC_API_KEY is set, click 'AI Legal Correction' and verify"
Write-Host "     the progress bar appears and the UI does not freeze"
Write-Host "  5. Click 'Export to Word (.docx)' and open the file in Word "
Write-Host "     verify Courier New 12pt, 1.5 inch left margin, 25 lines per page"
Write-Host "======================================================" -ForegroundColor Cyan
```

---

## STOPPING CONDITIONS

Stop immediately if:
- Step 1 reports any source file missing from Downloads
- Step 6 reports a syntax error in any .py file
- Step 9 unit tests fail
- pip install fails with an error (not a warning)

In all cases, report the exact error and do NOT proceed to the next step.
The backup created in Step 2 can be used to restore: just copy it back
over C:\Users\james\transcript_formatter\depo_formatter\

---

## WHAT THIS PROMPT DOES NOT DO

- Does NOT modify app_logging.py or file_loader.py (no changes needed)
- Does NOT change the .env file or API key
- Does NOT modify the venv itself, only installs packages into it
- Does NOT touch any files outside transcript_formatter\
- Does NOT commit to git (no git commands anywhere in this prompt)
- Does NOT delete the backup created in Step 2
