# README demo-gif scaffold (Fix Receipts)

Scaffold for the recording that fills the README's
`demo-gif-slot` comment in the Receipts section (retro ruling
2026-08-29, item 3: scaffold now, record deliberately). The take
is supervised: the chair reviews the gif before it ships — it is
the first-impression asset for the positioning's receipts story.

## One-time setup

```bash
brew install vhs
```

## Stage the scratch project

The demo needs a real, repeatable failure `attune fix` can repair.
Run this to (re)create it:

```bash
rm -rf /tmp/attune-fix-demo
mkdir -p /tmp/attune-fix-demo/src /tmp/attune-fix-demo/tests
cd /tmp/attune-fix-demo
git init -q
printf 'def greet():\n    return "hello"\n' > src/app_utils.py
printf 'from app_helpers import greet\n\ndef run():\n    return greet()\n' > src/app.py
printf 'import sys\nsys.path.insert(0, "src")\nfrom app import run\n\ndef test_run():\n    assert run() == "hello"\n' > tests/test_app.py
git add -A && git commit -qm "demo: broken import after rename"
```

The staged bug: `src/app.py` imports `app_helpers`, but the module
was renamed to `app_utils` — exactly the "imports resolve after
the rename" outcome the README's command states. The probe
(`pytest tests/test_app.py`) fails before the fix and passes after.

## Record

```bash
cd <attune-ai repo root>
vhs scripts/demo/fix-receipts.tape
```

- A real `attune fix --run` executes during the take — **API
  credits (~$1); the spend gate applies to every take.**
- After the first take, tune the tape's 45s workflow `Sleep` to
  the real wall-time, then re-record.

## Ship

1. Chair reviews `scripts/demo/fix-receipts.gif`.
2. On approval, commit the gif and replace the README's
   `<!-- demo-gif-slot: ... -->` comment with the image reference.
3. The gif is a binary — keep it small (target < 2 MB; drop
   `Set Theme`/size if needed) or host it via the repo's raw URL.

## Social preview card

`social-preview.html` is the source for the GitHub social preview
(the 1280x640 card shown when the repo link is shared);
`social-preview.png` is its 1x render, the shipping asset. The
html's header comment carries the regenerate recipe (Playwright
screenshot, optional `@fontsource/inter`). GitHub has no API for
this setting: a maintainer uploads the PNG at Settings -> General
-> Social preview. Salvaged 2026-09-04 from the
`archive/wip-pre-pull-2026-09-02` tag (retro item 5).
