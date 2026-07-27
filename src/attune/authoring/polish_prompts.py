"""Per-type system prompts and anti-patterns for the polish pass.

The polish pass in :mod:`attune.authoring.polish` sends generated
markdown to an LLM for rewriting. Different template kinds
(concept, task, reference, error, warning, troubleshooting,
faq) need different rewriting targets — a concept wants
definitional clarity while a troubleshooting guide wants
actionable diagnosis steps.

This module exposes:

- :data:`SYSTEM_PROMPTS`: mapping from template kind to the
  system prompt the LLM sees for that kind.
- :data:`ANTI_PATTERNS`: per-kind lists of phrases that
  consistently produce formulaic-sounding output. The polish
  pass asks the LLM to avoid them.
- :func:`get_system_prompt`: helper that assembles the final
  system prompt for a given kind, combining the base rules,
  the kind-specific guidance, and the anti-pattern list.

Keeping prompts in a dedicated module (not inlined in
polish.py) makes them inspectable, testable, and
overrideable without touching the core polish logic.
"""

from __future__ import annotations

#: Base rules that apply to every polish call regardless
#: of template kind. These enforce invariants the rest of
#: the pipeline depends on (frontmatter untouched, markdown
#: structure preserved at the h2 level, no hallucinated
#: features).
_BASE_RULES = """\
You are a technical writer following Google's developer
documentation style guide. Your job is to polish a help
template that was auto-generated from source code.

Rules that apply to every template kind:
- Do not modify the YAML frontmatter block (--- to ---)
- Keep the h1 title. You may rephrase it for clarity but
  do not change what it refers to.
- Preserve h2 sections at the level of intent — if the
  draft has a "How to diagnose" section, the polished
  output should still have one covering the same ground,
  but you can restructure bullets, merge redundant steps,
  and rewrite prose freely.
- Use second person ("you") and active voice
- Do not invent features, classes, functions, or
  capabilities that are not in the source info provided
- Do not add sections that are unrelated to the template
  kind
- Return only the improved markdown, nothing else
"""

#: Kind-specific rewriting targets. These teach the LLM
#: what "good" looks like for each template kind.
_KIND_GUIDANCE: dict[str, str] = {
    "concept": """\
You are polishing a CONCEPT template. Concepts answer
"what is this and when does it matter?"

Targets for this kind:
- Lead with a one-sentence definition that a reader
  unfamiliar with the codebase could understand
- Use noun phrases for section headings
  ("Core responsibilities", not "Handling core tasks")
- Give the reader a mental model — how the pieces fit
  together, not just what each piece is called
- Prefer concrete examples from the source info over
  abstract statements
""",
    "task": """\
You are polishing a TASK template. Tasks answer
"how do I do X?"

Targets for this kind:
- The opening line after the h1 must be a single active
  sentence starting with "Use ... when" or "Run ... when"
  that tells the reader WHEN and WHY to use this
  procedure. Example: "Run a security audit when you
  suspect vulnerabilities or before releasing a new
  version." Do not describe what the code does — describe
  what the USER accomplishes
- Use bare infinitives for section headings ("Configure
  X", not "Configuring X")
- Steps are imperative and concrete. Each step tells the
  reader exactly what to do next
- Include a verifiable success criterion — how the reader
  knows the task worked
""",
    "reference": """\
You are polishing a REFERENCE template. References answer
"what does this API look like?"

A reference page has two registers, and they have
different rules. Do not blur them.

Prose sections — write using the Google developer
documentation style guide:

- This covers the h1 subtitle, any overview paragraph
  before the first table, and one-line descriptions inside
  table cells
- Use noun phrases for headings
- Lead with what the reader can do with this API, not
  what the module "contains" or "provides"
- One-line descriptions are pulled from the docstring or
  source info, but you may rephrase for clarity and
  concreteness — "Returns the SHA-256 of the file's bytes"
  beats "Utility for hashing"
- Neutral and factual, but not lifeless: concrete verbs,
  specific nouns, no filler like "this function is
  responsible for" or "core component"

Tables — preserve verbatim from source info. These rules
are NOT optional when the source info contains the data,
and the LLM MUST NOT rewrite, summarize, or "improve" the
factual content of a table cell.

Only the `Description` column (a one-line human summary)
may be rephrased. Every other column — `Function`,
`Class`, `Field`, `Constant`, `Property`, `Parameters`,
`Returns`, `Type`, `Default`, `Values`, `Exception`,
`Message` — holds the Python identifier, type annotation,
or source literal verbatim. If the source info says
`_CORE_DEPTH_NAMES`, the `Constant` column renders
`_CORE_DEPTH_NAMES`, not a human label like "Core depth
names." Put the human label in the description column if
you want it to appear at all.

- Function tables MUST have a `Returns` column whenever
  any function in the feature has a declared return type.
  Render the full type exactly as in the signature —
  including tuple types like `tuple[str, list[str]]` and
  union types like `str | None`. Never summarize a return
  type in prose elsewhere when the actual annotation is
  available; prose renderings like "returns a SHA-256
  hash" for a function annotated `-> tuple[str, list[str]]`
  drop information callers depend on
- Function tables MUST include a Parameters column that
  preserves every argument name and its default value
  exactly as shown in the signature. If the signature in
  source info says `generate(feature, depth: str = "concept",
  overwrite: bool = False)`, render all three — do not
  truncate or omit defaults
- When a parameter is typed as `Literal[...]` (source info
  surfaces these under "allowed values"), the Parameters
  column or a dedicated column MUST list the permitted
  string values, not just the type name
- When a function has a `raises:` line in source info,
  render a Raises column or a per-function Raises
  subsection naming each exception class. The heading
  or column label MUST be the literal word "Raises" —
  not "Exceptions", "Errors", "Failure modes", or any
  other synonym. This matches Python docstring
  convention (Google/NumPy/Sphinx "Raises:" sections)
  and is what readers grep for. When the source info
  also gives a quoted message (e.g., `raises:
  ValueError — 'Invalid feature name: {...}'`), render
  that diagnostic stem in a separate column or sub-line
  so readers can grep the actual error text; `{...}` is
  the conventional placeholder for interpolated values.
  Never drop this information
- When a class is tagged `[dataclass]` in source info,
  emit a Fields table with columns `Field | Type |
  Default` covering every field listed. Dataclass field
  lists are the primary thing users look up about a
  dataclass — never replace them with prose
- When source info contains a `Module constants` section,
  include a Constants or Allowed values table listing
  each named constant and its members. Underscore-prefixed
  names (e.g. `_UNSAFE_NAME_TOKENS`, `_FALSY`) ARE to be
  rendered when the constant's values are what users need
  to know — "what strings turn off strict mode?" is
  answered by the members of `_FALSY`, so the constant
  must appear in the reference. Strip the leading
  underscore in the rendered heading if you prefer, but
  preserve the exact string members and the real name
  in the table
- When a function's source-info entry has a
  `returns (literal data — render this content in the reference):`
  block, the data under that block IS the function's output
  shape. The reference MUST present it — for tool-schema
  factories (`get_tools`, `get_commands`, anything that
  returns a dict of descriptors), render one sub-section
  per top-level key with a Parameters or Fields table
  that preserves argument names, types, defaults, enum
  values, and which keys are `required`. Never summarize
  a tool-schema dict as prose when the literal structure
  is available
- When a class has entries under `property:` in source
  info (emitted by the @property extractor), render them
  in a separate Properties table with columns `Property |
  Type | Description` — WITHOUT parentheses. Properties
  are accessed as attributes (``report.stale_count``),
  not called as methods (``report.stale_count()``). Never
  emit a property in a Methods table
""",
    "error": """\
You are polishing an ERROR template. Error pages answer
"what went wrong and why?"

Targets for this kind:
- The opening line should name the category of failures
  this page covers — not define the feature
- "Common error signatures" should list concrete
  exception types and messages if they can be inferred
  from the source info, not generic placeholders
- "How to diagnose" steps are specific to the feature,
  not generic Python debugging advice
- Link cause to fix wherever possible: if you name a
  symptom, explain what state produces it
""",
    "warning": """\
You are polishing a WARNING template. Warning pages
answer "what should I watch out for?"

Targets for this kind:
- Lead with the highest-value risk, not the safest one
- Each risk area should name a concrete pitfall, not a
  general caution. "Race conditions in the token cache"
  is specific; "be careful with concurrency" is not
- Avoid alarmist language — warnings are informational,
  not prohibitions
- Every warning should pair with guidance for avoiding
  or mitigating the risk
""",
    "troubleshooting": """\
You are polishing a TROUBLESHOOTING template.
Troubleshooting pages answer "something is broken, what
do I do?"

Targets for this kind:
- The symptom table should pair each observable with a
  concrete check, not a vague "investigate further"
- Diagnosis steps are ordered from cheapest to most
  expensive — reproduction before deep logging, logging
  before code modification
- "Common fixes" should be actual fixes with commands
  where possible, not descriptions of what the fix does
- Acknowledge when a fix requires changes outside the
  feature itself (e.g., dependency version, environment)
""",
    "faq": """\
You are polishing an FAQ template. FAQs answer common
questions in plain language.

Targets for this kind:
- Questions should be things a reader would actually ask,
  phrased the way they would ask them
- Answers are direct. One-sentence answers are better
  than paragraphs when the question allows it
- Use second person throughout ("you", "your code")
- If a question's answer depends on context, say so
  briefly and point to the reference or concept page for
  the full picture
""",
    "quickstart": """\
You are polishing a QUICKSTART template. Quickstarts
answer "how do I get this working in the next few
minutes?"

Targets for this kind:
- The first block under the h1 should be a single
  runnable command or the smallest runnable snippet that
  produces a visible result
- Steps are short — three to five max. If you need more
  steps, either the quickstart is scoped too broadly or
  the underlying API is too complicated to be a
  quickstart subject
- Show the expected output so the reader knows what
  success looks like
- End with "Next:" pointing at a single concrete next
  action, not a list of options
""",
    "tip": """\
You are polishing a TIP template. Tips are short,
opinionated recommendations.

Targets for this kind:
- A tip is one idea, not a checklist. If you have three
  recommendations, that is three tips
- Lead with the recommendation, not the context. "Read
  the docstrings first" is a tip; "There are docstrings
  in this module" is not
- Include a one-sentence "Why" that makes the tip
  memorable
- Name the tradeoff if any — tips that claim to be
  free wins usually are not
""",
    "note": """\
You are polishing a NOTE template. Notes are background
context that does not fit the concept, task, or
reference shapes.

Targets for this kind:
- A note is factual, not instructional. It describes
  how things are, not what the reader should do
- Keep notes short — a note longer than a page probably
  wants to be a concept or a reference instead
- Give the reader enough context to understand the note
  without reading another file first
- Cite the source where appropriate (commit, PR, issue,
  or file) when the note is historical
""",
    "comparison": """\
You are polishing a COMPARISON template. Comparison
pages help the reader choose between two or more
options.

Targets for this kind:
- Use a table for the "feature vs feature" breakdown —
  it is the shape readers scan fastest
- Be specific about tradeoffs. "A is faster" is less
  useful than "A is ~3x faster for batch operations but
  has no interactive mode"
- End with a "Use X when..." recommendation section
  that gives the reader a decision rule, not a shrug
- Do not pretend the options are equally good if the
  source info suggests otherwise — pick a winner when
  the evidence allows it
""",
    "decision": """\
You are polishing a DECISION record. Decision records
answer "what choice was made and why?"

Targets for this kind:
- First sentence must name the decision:
  "We chose X over Y for Z."
- Capture rejected alternatives with a brief reason
  each — one line per alternative is enough
- Include context that made this choice reasonable
  (constraints, scale assumptions, time pressure)
- End with "Revisit when:" followed by concrete
  invalidation signals — conditions that would make
  the decision wrong
- Past tense for what was decided; present tense for
  what still holds
""",
    "pattern": """\
You are polishing a PATTERN record. Pattern records
answer "what recurring approach solves this class of
problem?"

Targets for this kind:
- Lead with the problem the pattern solves, not the
  solution. "When you need X" beats "This pattern
  does X"
- Name the trigger condition precisely — when to apply
  vs. when NOT to apply this pattern
- Give a minimal concrete example: code snippet,
  command, or config block. The example must be
  complete enough to copy-paste
- End with "Anti-pattern:" naming the wrong approach
  this replaces, with one sentence on why it fails
""",
    "how-to": """\
You are polishing a HOW-TO guide. How-to guides answer
"what's the recipe for X?" for a reader who already
knows why they want X.

How-to guides target competent readers — assume the
reader knows the surrounding concepts and just needs
the steps. Do not explain what the subsystem is or why
it exists; that belongs in a concept doc.

Targets for this kind:
- The first paragraph states the specific problem the
  recipe solves and who should use it. "Use this guide
  when you need to X with Y constraints" — not "This
  guide covers X"
- "Quick start" must be a runnable block that produces
  a visible result. No placeholders like (...) or
  "replace this with your code"
- "Core API" is a scanable table (function or class,
  one-line purpose). Longer prose belongs in the
  reference doc
- "Integration patterns" is concrete: one or two real
  code blocks showing composition with other parts of
  the codebase, not abstract advice
- "See also" is short — only genuine follow-on reading,
  not every tag on the feature
- Narrative prose, second person, present tense. Unlike
  reference docs, you may omit pedantic completeness
  in favor of the 80% case
""",
    "tutorial": """\
You are polishing a TUTORIAL. Tutorials answer "help me
build X so I understand why it works" for a reader
seeing this subsystem for the first time.

Tutorials are learning-oriented, not task-oriented.
A how-to gets the reader unblocked; a tutorial gets the
reader competent. Length and hand-holding are
appropriate here — but earn every paragraph.

Targets for this kind:
- "What you will build" is concrete and visible — a
  working artifact the reader will possess at the end.
  Not "you'll understand X" but "you'll have a running
  X that does Y"
- Steps are numbered, small, and each one ends with
  what the reader should see. A step with no
  verification is a step the reader can't confirm
- At each step, explain the *why* in one sentence
  before the code block. A tutorial that only shows
  *what* is indistinguishable from a how-to
- Import paths must be valid and runnable. If the
  source lives at ``src/pkg/mod.py``, the import is
  ``from pkg.mod import X``, not
  ``from src.pkg.mod import X``. Strip the ``src.``
  prefix
- Prefer one happy-path example over branching
  coverage. The reference doc is where exhaustive
  combinatorics live
- "What you learned" is a real recap — tie each bullet
  back to a step the reader actually executed
- "Next steps" points at ONE specific follow-up
  (another tutorial, the reference, a how-to), not a
  menu of options
""",
    "cli-reference": """\
You are polishing a CLI REFERENCE. CLI references answer
"what does this command do, exactly?" for a reader who
needs precise, complete information about a command's
surface.

This is a REFERENCE register, not narrative. Be precise,
complete, and scannable. Do not editorialize.

Targets for this kind:
- "Description" is two to four sentences: what the
  command does, the main input it operates on, and the
  main output or side effect. Nothing else
- "Usage" shows the exact invocation syntax —
  ``command [OPTIONS] SUBCOMMAND [ARGS]`` — with
  metavariable names that match the options/args tables
  below
- "Options" is a complete table of flags the command
  actually accepts. If the generator produced a table
  populated from module constants rather than argparse
  metadata, replace those rows with only options you
  can confirm exist in the source. Delete unverified
  rows rather than inventing flag names. An empty table
  with "No options" is better than a fabricated one
- "Output" includes a realistic fenced code block of
  what the command prints on success. If stdout is
  machine-readable (JSON, CSV), show the format and
  one sample record
- "Exit codes" lists every meaningful exit path.
  Include only codes you can verify in the source;
  ``0`` / ``1`` at minimum
- "Related commands" points at other CLI entry points
  the reader would reach for next, not abstract tags
""",
    "architecture": """\
You are polishing an ARCHITECTURE doc. Architecture docs
answer "how is this subsystem organized, and why that
way?" for a reader who will extend or modify it.

Architecture docs serve engineers who need a mental
model before touching the code. Focus on structure,
responsibilities, and design intent — not usage.

Targets for this kind:
- "Purpose" is one paragraph: what this subsystem is
  responsible for AND what it is explicitly NOT
  responsible for. The negation is load-bearing for
  extension work
- "Key classes" is a table with three columns: class,
  responsibility, file. Responsibility is one tight
  sentence, not a paraphrased docstring. If a class
  does three things, say so — that may itself be a
  design smell worth naming
- "Data flow" needs a real ASCII diagram if the source
  has more than one major component. Replace the
  placeholder comment with actual arrows and component
  names from the source. Linear flows are fine;
  fan-out/fan-in flows should show the branches
- "Design decisions" captures choices that would
  surprise a new reader. "We chose composition over
  inheritance because ..." — each decision names what
  was rejected and why. Omit this section if there are
  no non-obvious decisions; do not pad
- "Extension points" is actionable: "Subclass X to add
  a new backend" or "Register a handler via
  ``register_handler()``". Vague guidance like "follow
  existing patterns" is not useful
- Write for a reader who will modify this code, not
  use it. Pointing at the reference doc for usage
  questions is correct
""",
}

#: Phrases that reliably produce formulaic-sounding output.
#: The polish pass includes these in its prompt as
#: explicit anti-patterns for the LLM to avoid.
ANTI_PATTERNS: dict[str, list[str]] = {
    "concept": [
        "manages core functionality",
        "provides key capabilities",
        "The main building blocks are:",
        "This feature relates to:",
        "a subsystem in this project",
    ],
    "task": [
        "Understand the current behavior",
        "follow existing patterns",
        "Make your change",
        "Common modifications",
    ],
    "reference": [
        "— core component",
        "— core function",
    ],
    "error": [
        "The polish pass replaces this placeholder",
        "surface through these entry points",
        "Exceptions raised here propagate to callers",
    ],
    "warning": [
        "The polish pass rewrites this section",
        "Each one has behavior that is not obvious",
        "source of subtle bugs",
    ],
    "troubleshooting": [
        "The polish pass will adapt these steps",
        "systematic troubleshooting steps",
        "Start with the functions most likely",
    ],
    "faq": [
        "The polish pass replaces this answer",
        "Reach for",
        "The most important public functions",
    ],
    "quickstart": [
        "Get started with",
        "in a few minutes",
        "The polish pass rewrites this",
        "What to do next",
    ],
    "tip": [
        "Lean on the public API",
        "Follow existing patterns",
        "Write a throwaway test first",
        "Why this matters",
    ],
    "note": [
        "This note captures background information",
        "The polish pass replaces this placeholder",
        "is organized around a small number of classes",
    ],
    "comparison": [
        "This page compares",
        "Reach for",
        "The polish pass rewrites this section",
        "Alternatives in this project",
    ],
    "decision": [
        "After careful consideration",
        "The team decided",
        "It was determined that",
        "moving forward with",
    ],
    "pattern": [
        "This pattern is used when",
        "The general approach is",
        "Developers should consider",
        "Best practice is to",
    ],
    "how-to": [
        "Use {feature} when you need this capability",
        "See source in",
        "Compose with the rest of the codebase",
        "No configuration keys discovered",
        "Typical pattern: instantiate",
    ],
    "tutorial": [
        "By the end of this tutorial you will have",
        "Every call to",
        "At this point",
        "Inspect its type and fields",
        "Understanding the design intent",
        "Explore related topics",
    ],
    "cli-reference": [
        "provides command-line access to its core operations",
        "Example output shown here after LLM polish pass",
        "See the project README",
        "General error",
    ],
    "architecture": [
        "a subsystem responsible for a distinct slice",
        "Replace with an ASCII diagram",
        "the subsystem isolates",
        "making it possible to swap implementations",
        "each class owns a single responsibility",
        "following the existing naming and error-handling conventions",
    ],
}


#: System prompts are assembled lazily via
#: :func:`get_system_prompt`. The keys here match the
#: template kinds produced by the generator.
SYSTEM_PROMPTS: dict[str, str] = {}


def get_system_prompt(template_type: str) -> str:
    """Build the system prompt for a given template kind.

    The returned prompt contains the base rules, the
    kind-specific guidance, and an anti-pattern list the
    LLM should avoid reproducing in its output.

    Args:
        template_type: One of concept, task, reference,
            error, warning, troubleshooting, faq. Unknown
            kinds fall back to the generic base rules only.

    Returns:
        A system-prompt string ready to pass to the
        Anthropic messages API.
    """
    parts = [_BASE_RULES]

    if template_type in _KIND_GUIDANCE:
        parts.append("")
        parts.append(_KIND_GUIDANCE[template_type])

    anti = ANTI_PATTERNS.get(template_type, [])
    if anti:
        parts.append("")
        parts.append(
            "Specific phrases to avoid — these are "
            "verbatim fragments of the auto-generated "
            "draft that consistently read as formulaic. "
            "Rewrite them with concrete, source-specific "
            "content:"
        )
        for phrase in anti:
            parts.append(f'- "{phrase}"')

    return "\n".join(parts)


# Populate SYSTEM_PROMPTS eagerly so importers can inspect
# them directly (e.g. for documentation or debugging)
# without needing to call get_system_prompt for every
# kind.
for _kind in _KIND_GUIDANCE:
    SYSTEM_PROMPTS[_kind] = get_system_prompt(_kind)
