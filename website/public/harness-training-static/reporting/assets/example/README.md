# Create an activity report

Use Python 3.12 or later. This program uses Python's standard library and makes
no model or network call. The commands below reuse the explicit Python
interpreter from your course environment.

## Select the course interpreter

If this terminal already has `COURSE_PYTHON` set from the course, keep that
value. Otherwise, open a terminal in your course folder—the folder containing
its `.venv`—and restore the paths for your shell. If you have not created the
course environment, follow [Get started](https://smartaimemory.com/harness/help/get-started/)
first. The Windows course route selects x64 CPython 3.12 explicitly, including
on ARM64 hardware where it runs under emulation.

If you used a custom course environment, set `COURSE_PYTHON` to its full Python
path instead of the default `.venv` path below.

**Windows PowerShell 5.1 or 7**

```powershell
$COURSE_WORK = (Get-Location).Path
$COURSE_PYTHON = Join-Path $COURSE_WORK '.venv\Scripts\python.exe'
& $COURSE_PYTHON --version
```

**macOS/Linux — Bash or Zsh**

```sh
COURSE_WORK="$(pwd -P)"
COURSE_PYTHON="$COURSE_WORK/.venv/bin/python"
"$COURSE_PYTHON" --version
```

Expect Python 3.12 or later. Stop if the selected interpreter cannot run. No
activation script or execution-policy change is needed.

Keep this terminal open and change to the extracted example folder containing
`report.py` and `data/activity.csv`. Keep `COURSE_PYTHON` pointing to the course
interpreter when you change folders.

## Generate the report

**Windows PowerShell 5.1 or 7**

```powershell
& $COURSE_PYTHON report.py data/activity.csv --format html --output activity-report.html
```

**macOS/Linux — Bash or Zsh**

```sh
"$COURSE_PYTHON" report.py data/activity.csv --format html --output activity-report.html
```

Expect `Saved report to activity-report.html`. Open that file in your browser.
The six synthetic entries total 270 minutes: Orion 180 and Lumen 90;
Development 150, Documentation 75 and Testing 45. Dates cover October 19–21,
2026. The input file remains unchanged. An existing destination is refused;
choose a new output filename for another run.

For a text report, run the command for your shell:

**Windows PowerShell 5.1 or 7**

```powershell
& $COURSE_PYTHON report.py data/activity.csv
```

**macOS/Linux — Bash or Zsh**

```sh
"$COURSE_PYTHON" report.py data/activity.csv
```

## Check the result

With pytest installed in the selected course environment:

**Windows PowerShell 5.1 or 7**

```powershell
& $COURSE_PYTHON -m pytest -q tests/test_report.py tests/test_html_report.py
```

**macOS/Linux — Bash or Zsh**

```sh
"$COURSE_PYTHON" -m pytest -q tests/test_report.py tests/test_html_report.py
```

The expected HTML and text files are in `expected/`. The byte contract for
report output and the success confirmation is UTF-8 with LF (`\n`) line endings.
The checks compare captured stdout directly with the expected bytes; they do
not normalize Windows CRLF line endings. Use `--output` to create a report file.

`current-checks.json` is a retained historical receipt despite its filename.
It records 77 passing cases and a bounded Harness 1.7.0 workflow on macOS with
Python 3.12.2 on November 5, 2026. Its source hashes and limits describe that
prior observation. It does not qualify this Windows onboarding candidate or
establish a current Windows workflow pass. Keep the receipt unchanged and
record any new run separately.

Project filtering is a proposed course exercise; this program has no project
filter option. Keep the original CSV and checks when planning a change.
