# Create an activity report

Use Python 3.12 or later. Run these commands from the extracted folder containing
`report.py` and `data/activity.csv`. The program uses Python's standard library
and makes no model or network call.

```sh
python3.12 report.py data/activity.csv --format html --output activity-report.html
```

Expect `Saved report to activity-report.html`. Open that file in your browser.
The six synthetic entries total 270 minutes: Orion 180 and Lumen 90;
Development 150, Documentation 75 and Testing 45. Dates cover October 19–21,
2026. The input file remains unchanged. An existing destination is refused;
choose a new output filename for another run.

For a text report:

```sh
python3.12 report.py data/activity.csv
```

On Windows, use `py -3.12` in place of `python3.12`. That substitution is
guidance; this course's fresh check record describes the actual macOS run.

## Check the result

With pytest installed in the selected environment:

```sh
python3.12 -m pytest -q tests/test_report.py tests/test_html_report.py
```

The current course check passed 77 cases without failures or skips. Read
`current-checks.json` for its source hashes, environment and
limits. The expected HTML and text files are in `expected/`.

Project filtering is a proposed course exercise; this program has no project
filter option. Keep the original CSV and checks when planning a change.
