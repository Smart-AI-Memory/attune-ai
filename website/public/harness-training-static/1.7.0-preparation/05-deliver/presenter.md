# Presenter notes: Make the tool usable

Harness 1.7.0. Derived from this lesson’s JSON.

## section-1: Make the useful result easy to obtain

A report is more useful when another person can generate it from the instructions, recognize its output and recover from a common problem.

- Let the learner say who would use the report and what they need to do with it.
- Opening a supplied report is not a new AI build.

## section-2: Find the folder the commands need

The command is short. Selecting the correct extracted folder is the prerequisite that makes it work.

- Allow time for extracting and selecting the folder. Do not assume the learner knows the current working directory.
- Use the actual download link. Do not invent a browser extraction control or promise the same folder name across extraction tools.

## section-3: Create a report you can open

From the extracted example folder, run the program on the supplied synthetic CSV and choose a new output filename.

- This argv is verified against the bundled parser and README: one CSV path, --format html and --output path.
- A refusal to overwrite is expected behavior, not a reason to delete the previous result. No fresh execution is claimed by the lesson text.

## section-4: Connect the report to its source

A successful file write tells you a file was created. Check that it contains the result you intended.

- Ask the learner to find their generated file rather than reopening the supplied expected file by mistake.
- Software checks, the learner’s execution and a print preview are distinct evidence.

## section-5: Change a copy and predict the result

Practice changing input without losing the original six-row fixture or a previous report.

- This variation is optional and should use a separate input and output. Preserve the supplied fixture and any earlier learner result.
- The test suite uses the original fixture, so changing a practice copy should not rewrite its baseline.

## section-6: Give the next person one clear route

Write instructions around the actual folder, command, expected result and common refusal.

- Ask whether a reader can obtain every input and distinguish expected from observed output.
- Record help needed when someone tries the instructions; do not infer a measured learning outcome from completion.

## section-7: Know what is ready and what still needs checking

You can now explain how to obtain the report and how to preserve a previous result.

- The optional check never locks the next lesson.
- Invite the learner to explain a recovery decision with less prompting.
