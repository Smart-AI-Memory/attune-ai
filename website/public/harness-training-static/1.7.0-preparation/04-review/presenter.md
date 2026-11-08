# Presenter notes: Decide whether to trust the report

Harness 1.7.0. Derived from this lesson’s JSON.

## section-1: Decide what makes this report trustworthy

A useful report gives you an answer you can explain, together with evidence for the parts you cannot check by eye.

- Open the actual current-course report. Inspect its numbers rather than relying on a screenshot.
- The benefit is explaining why a result is supported and naming its limits.

## section-2: Check one answer yourself

The six-row fixture is small enough to audit without reading the implementation.

- Let the learner calculate one subtotal. Do not replace the activity with a recital of the answer.
- The CSV and expected report are primary artifacts; the table is derived from their six rows.

## section-3: Read the recorded result within its scope

A check is useful when you can identify the input, expected answer, command and actual result.

- Use the fresh current-checks.json that accompanies this course. Do not import a result from another runtime or source.
- The current record reports 77 reporting tests in a fresh Python 3.12 environment. Keep its exact source, environment and result with the course.

## section-4: Turn a concern into a checkable question

A plausible concern deserves a concrete input and expected result before you decide whether it is a defect.

- Label the missing-row case as illustrative. Do not attribute it to a reviewer or an actual run.
- Ask what evidence would change the learner’s decision.

## section-5: Handle a real finding without changing the answer

When evidence establishes a defect, preserve the expectation and make the correction inspectable.

- Keep a hypothetical repair separate from the current software-check result.
- Changing the expected answer changes the contract; it is not a shortcut to green tests.

## section-6: Notice when a plausible total is wrong

The omitted-row example lets you practice checking a result with fewer hints.

- Keep the optional check nonblocking. Invite an explanation rather than merely choosing an option.
- The omitted-row numbers are independently calculated expectations, not a software failure report.

## section-7: Leave an explanation another person can inspect

Use a short note to connect the useful result, checked claims and next decision.

- Ask the learner to name one supported claim and one remaining limit.
- Keep the note concise and do not score writing style or force a response.
