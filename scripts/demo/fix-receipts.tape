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

# The take: the README's own command, verbatim shape.
Type `attune fix "imports resolve after the rename" --scope src/app.py --probe "pytest tests/test_app.py" --run`
Sleep 800ms
Enter

# Let the contract preview, diff attribution, and probe re-run
# scroll through. Tune this after the first supervised take —
# real workflow wall-time varies.
Sleep 45s

# Hold the receipt (exit 0, probes passed) on screen.
Sleep 4s
