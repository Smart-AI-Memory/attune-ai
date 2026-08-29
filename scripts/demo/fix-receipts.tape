# vhs tape — README demo-gif for the Fix Receipts block
# (retro 2026-08-29 item 3, ruled scaffold-then-record).
#
# Renders the exact command the README's Receipts section shows,
# against the scratch repo scripts/demo/README.md stages. Run with:
#   vhs scripts/demo/fix-receipts.tape
# Produces scripts/demo/fix-receipts.gif — chair reviews BEFORE it
# fills the README's demo-gif slot. A real `attune fix --run` bills
# API credits (~$1): the spend gate applies to every take.

Output scripts/demo/fix-receipts.gif

Set FontSize 15
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms

# Stage: cd into the scratch project prepared per the demo README.
Hide
Type "cd /tmp/attune-fix-demo"
Enter
Type "clear"
Enter
Show

# The take. NOTE: --workflow fix is REQUIRED for --run (discovered
# in the 2026-08-29 timed run — Fix never guesses a route; the
# README's own command needs the same correction).
Type `attune fix "imports resolve after the rename" --workflow fix --scope src/app.py --probe "pytest tests/test_app.py" --run`
Sleep 800ms
Enter

# Timed 2026-08-29: the real run took ~16.4s end to end.
Sleep 22s

# Hold the receipt (exit 0, probes passed) on screen.
Sleep 5s
