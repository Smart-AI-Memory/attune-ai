# RAG-Grounded Code Generation (Multi-Package, Multi-LLM)

**Version:** 4.0 (general-purpose attune-rag + pluggable
corpus + provider adapters)
**Status:** Planning
**Created:** 2026-04-17
**Owner:** Patrick Roebuck
**Scope:** new `attune-rag` package (LLM-agnostic,
corpus-pluggable, with optional provider extras) +
`attune-ai` 6.0.0 + `attune-author` 0.4.0. `attune-help`
unchanged.

## Positioning

`attune-rag` is a **standalone, general-purpose RAG library**
that attune happens to use first. It:

- Is **LLM-agnostic** — pipeline returns a prompt string;
  send it to any LLM.
- Has **pluggable corpus** — use attune-help (default),
  any markdown directory, or your own `CorpusProtocol`
  implementation.
- Ships **optional provider adapters** for Claude, OpenAI,
  and Gemini via extras (`attune-rag[claude|openai|gemini|all]`).
- Depends on **zero LLM SDKs at install time** — all
  provider deps are optional extras.

---

## Context

- `attune-help` v0.5.1 ships **633 bundled markdown files**
  across 11 categories plus `summaries.json` and
  `cross_links.json` in `attune_help/templates/`. This is
  the canonical RAG knowledge base.
- `attune-author` v0.3.9 generates and maintains templates
  via `attune-author generate` CLI + `attune-author-mcp`
  server. Core entry point: `generate_feature_templates()`.
- `attune-ai` currently imports only `_extract_preamble`
  from attune-help (`src/attune/help/preamble.py`).
- `BaseWorkflow` is SDK-native: modern workflows delegate to
  `claude_agent_sdk.query()` subagents and return
  `WorkflowResult`.
- `src/attune/help/feedback.py` already provides
  `record_template_feedback()` + `get_template_confidence()`.
- **Prior lesson (CLAUDE.md):** `sentence-transformers` was
  removed — 0.4% savings, 420MB dep. Anthropic's server-side
  prompt caching (90% discount) supersedes client-side caching.

---

## Problem

LLM code generation in `attune-ai` workflows and content
generation in `attune-author` can hallucinate attune-specific
APIs, workflow names, CLI commands, and patterns. The 633
files in attune-help are an authoritative corpus but are not
automatically consulted. Users cannot see which help
documents grounded a code or content output, so they have no
basis for trusting generated output over their own memory of
the codebase.

Additionally: putting retrieval logic inside `attune-ai`
creates a circular-looking dep if `attune-author` wants to
consume it without pulling all of attune-ai.

---

## Goals

1. **Ground generated code and content** in a markdown
   corpus (attune-help by default, any directory optionally)
   so outputs cite real APIs, workflows, patterns.
2. **Source provenance in v1** — citations in every output
   from the attune-ai RAG workflow and the attune-author
   generate path.
3. **Grounded-by-default** for `attune-author generate`
   (with `--no-rag` opt-out + `ATTUNE_AUTHOR_RAG=0` env).
4. **LLM-agnostic core.** Pipeline returns a prompt string;
   consumers choose the LLM. Optional provider extras for
   Claude, OpenAI, Gemini.
5. **Pluggable corpus.** Default `AttuneHelpCorpus`; also
   ship `DirectoryCorpus` for arbitrary markdown dirs; allow
   users to implement `CorpusProtocol` for DBs, git trees, etc.
6. **Clean dep graph:** `attune-help` (corpus default) →
   `attune-rag` (retrieval, LLM-agnostic) → `attune-ai` /
   `attune-author` / external users (consumers). One-way.
7. **Measure hallucination reduction** via golden queries.
8. Hit p50 latency < 500ms cached / < 2s uncached for
   retrieval-only paths. LLM call latency is provider-dependent
   and not gated by this plan.

---

## End State

### Filesystem layout (sibling-repo pattern)

Matches the established `attune-author` / `attune-help`
pattern. The `attune-rag` package source lives in its own
git repo at `/Users/patrickroebuck/attune-rag/` (published
to PyPI as `attune-rag`, to GitHub as
`Smart-AI-Memory/attune-rag`). `attune-ai` contains only a
**pointer stub** at `packages/attune-rag/README.md` plus the
workspace-source entry in its `pyproject.toml`.

In the tasks below, paths of the form
`packages/attune-rag/<...>` refer to files **inside the
attune-rag sibling repo root**, except for the explicit
stub `packages/attune-rag/README.md` which is in the
attune-ai repo. Task 1.1 creates both.

### New package: `attune-rag` 0.1.0

```
attune-rag/
├── pyproject.toml               # core deps: jinja2, structlog
│                                # optional extras:
│                                #   [attune-help]  -> attune-help
│                                #   [claude]       -> anthropic
│                                #   [openai]       -> openai
│                                #   [gemini]       -> google-genai
│                                #   [all]          -> all of the above
├── README.md                    # quick starts for 3 LLMs + custom corpus
├── src/attune_rag/
│   ├── __init__.py              # RagPipeline, CitationRecord,
│   │                              KeywordRetriever, RagResult,
│   │                              CorpusProtocol, DirectoryCorpus
│   ├── pipeline.py              # orchestration + run_and_generate
│   ├── retrieval.py             # KeywordRetriever + RetrieverProtocol
│   ├── corpus/
│   │   ├── __init__.py          # exports
│   │   ├── base.py              # CorpusProtocol + RetrievalEntry
│   │   ├── directory.py         # DirectoryCorpus (markdown dir)
│   │   └── attune_help.py       # AttuneHelpCorpus (opt. dep)
│   ├── provenance.py            # CitationRecord + format_citations
│   ├── prompts.py               # augmented prompt templates
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py              # LLMProvider protocol
│   │   ├── claude.py            # opt. dep on anthropic
│   │   ├── openai.py            # opt. dep on openai
│   │   └── gemini.py            # opt. dep on google-genai
│   ├── benchmark.py             # python -m attune_rag.benchmark
│   └── cli.py                   # `attune-rag query "..."` debugger
└── tests/
    ├── unit/
    │   ├── test_pipeline.py
    │   ├── test_retrieval.py
    │   ├── test_corpus_directory.py
    │   ├── test_corpus_attune_help.py  # skipif attune-help missing
    │   ├── test_provenance.py
    │   ├── test_prompts.py
    │   └── providers/
    │       ├── test_claude.py   # mocked SDK
    │       ├── test_openai.py   # mocked SDK
    │       └── test_gemini.py   # mocked SDK
    └── golden/
        ├── queries.yaml         # 15+ golden queries
        └── test_golden.py
```

### `attune-ai` 6.0.0

- New workflow `src/attune/workflows/rag_code_gen.py`
  (BaseWorkflow subclass) depending on `attune-rag>=0.1.0`.
- New MCP tool `rag_knowledge_query` in
  `src/attune/mcp/tool_schemas.py` + handler in
  `workflow_handlers.py`.
- Registered in `_DEFAULT_WORKFLOW_NAMES`.
- Feedback integration via existing `help/feedback.py`.
- Version bump across all tracked files (see task 4.3).

### `attune-author` 0.4.0

- `--no-rag` flag on `attune-author generate`.
- `ATTUNE_AUTHOR_RAG=0` env to disable globally.
- Default: RAG on, logs a one-line notice that grounding
  is active and points at docs.
- Feature flag behind env var `ATTUNE_AUTHOR_RAG_DEFAULT`
  (default `1`) so we can flip the default remotely for 1-2
  releases if telemetry shows issues.

### Coordinated release artifacts

- Website page: new "Grounded code generation" section
  under [attune-ai website — verify with agent before edits].
- README updates in `attune-ai` and `attune-author`.
- CHANGELOG entries on both.
- Migration note for `attune-ai` 6.0.0 explaining no-op
  upgrade for non-RAG users.

---

## Non-Goals (v1)

- **No sentence-transformers by default.** Embedding
  strategy is benchmark-gated in task 2.4.
- **No custom caching layer.** `functools.lru_cache` for
  corpus loads only. Anthropic server-side caching handles
  LLM-level caching.
- **attune-help stays unchanged.** No new release.
- **No PromptMixin across all attune-ai workflows.** Only
  the dedicated `rag-code-gen` workflow.
- **No fine-tuning / RLHF.** Feedback is captured; what to
  do with it is a later spec.

---

## Phase 1: `attune-rag` package (new)

<task id="1.1" name="scaffold-attune-rag-package">
  <objective>
    Create the attune-rag package as a sibling git
    repository at /Users/patrickroebuck/attune-rag/
    (mirroring the attune-author / attune-help pattern).
    Add a pointer stub in attune-ai at
    packages/attune-rag/README.md and wire editable dev
    resolution via [tool.uv.sources].
  </objective>

  <context>
    <existing-code path="packages/attune-author/README.md">
      Existing stub: points to
      https://github.com/Smart-AI-Memory/attune-author,
      notes the sibling-clone layout, documents the
      [tool.uv.sources] entry. Our stub follows the same
      template verbatim (adjusted for rag).
    </existing-code>
    <existing-code path="pyproject.toml">
      [tool.uv.sources] already has entries for
      attune-author and attune-help. Add attune-rag with
      path = "../attune-rag", editable = true.
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-rag/pyproject.toml">
      name: attune-rag
      version: 0.1.0
      python: ">=3.10"
      description: "Lightweight, LLM-agnostic RAG pipeline
                    with pluggable corpora. Works with Claude,
                    OpenAI, Gemini, or any LLM."
      dependencies: ["structlog>=24.0", "jinja2>=3.1",
                     "pyyaml>=6.0"]
      # NO LLM SDK or attune-help at install time.
      optional-dependencies:
        attune-help: ["attune-help>=0.5.1,<0.6"]
        claude:      ["anthropic>=0.40"]
        openai:      ["openai>=1.40"]
        gemini:      ["google-genai>=1.0"]
        all:         ["attune-rag[attune-help,claude,openai,gemini]"]
        dev:         ["pytest>=8", "pytest-cov", "ruff",
                      "black", "attune-rag[all]"]
      build-system: hatchling (matches attune-author)
    </file>
    <file path="packages/attune-rag/src/attune_rag/__init__.py">
      Public exports: RagPipeline, CitationRecord, RagResult,
      KeywordRetriever, build_augmented_prompt. Module
      docstring links back to this plan.
    </file>
    <file path="packages/attune-rag/README.md">
      Sections:
        1. What it is (one-paragraph positioning)
        2. Install (core + optional extras table)
        3. Quickstart with Claude
             pip install 'attune-rag[attune-help,claude]'
             then 6-line example using
             RagPipeline().run_and_generate(query, "claude")
        4. Quickstart with OpenAI (same, [openai] extra)
        5. Quickstart with Gemini (same, [gemini] extra)
        6. Custom corpus example (DirectoryCorpus)
        7. No-LLM usage (just retrieve + build prompt,
           feed to anything)
        8. Link to attune-ai docs for full walkthrough.
    </file>
    <file path="packages/attune-rag/LICENSE">
      Apache 2.0 (match attune-ai license). NOTE: this
      LICENSE lives inside the attune-rag SIBLING REPO, not
      the attune-ai repo.
    </file>
    <file path="packages/attune-rag/tests/__init__.py">
      Empty marker (inside the sibling repo).
    </file>
  </files-to-create>

  <files-to-create>
    <!-- Files inside the attune-ai repo -->
    <file path="<attune-ai>/packages/attune-rag/README.md">
      Pointer stub. Mirrors
      packages/attune-author/README.md verbatim with names
      adjusted. Links to:
        - GitHub: https://github.com/Smart-AI-Memory/attune-rag
        - PyPI:   https://pypi.org/project/attune-rag/
      Shows install snippets for core + each optional extra
      and documents the sibling-clone layout.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="<attune-ai>/pyproject.toml">
      <change location="[tool.uv.sources]">
        AFTER: add
          attune-rag = { path = "../attune-rag", editable = true }
        (mirroring the existing attune-author / attune-help
        entries).
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv sync --extra dev --extra developer succeeds</check>
    <check>uv run python -c "import attune_rag"</check>
    <check>pytest packages/attune-rag/tests/ collects 0 tests without error</check>
    <check>uv lock is up to date (uv lock --check passes)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Workspace resolution differs between dev (sibling path)
      and production install (PyPI). Mitigation: publish
      attune-rag 0.1.0 to PyPI BEFORE attune-ai 6.0.0 so the
      version constraint resolves. Document this in task 4.4.
    </risk>
    <risk severity="low">
      Name collision on PyPI. Mitigation: check availability
      of "attune-rag" on PyPI before beginning. Reserve the
      name if needed.
    </risk>
  </risks>
</task>

<task id="1.2" name="corpus-protocol-and-directory">
  <objective>
    Define the CorpusProtocol interface and ship a
    DirectoryCorpus implementation that loads any directory
    of markdown files. This is the LLM-agnostic foundation;
    attune-help integration comes in task 1.3.
  </objective>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/corpus/__init__.py">
      Exports: CorpusProtocol, RetrievalEntry, DirectoryCorpus
    </file>
    <file path="packages/attune-rag/src/attune_rag/corpus/base.py">
      @dataclass(frozen=True) RetrievalEntry:
        path: str          # stable identifier within corpus
        category: str      # optional grouping (e.g. "concepts")
        content: str       # full markdown text
        summary: str | None
        related: tuple[str, ...]  # cross-link paths
        metadata: dict[str, Any]  # extensible

      class CorpusProtocol(Protocol):
        def entries(self) -> Iterable[RetrievalEntry]: ...
        def get(self, path: str) -> RetrievalEntry | None: ...
        @property
        def name(self) -> str: ...
        @property
        def version(self) -> str: ...
    </file>
    <file path="packages/attune-rag/src/attune_rag/corpus/directory.py">
      class DirectoryCorpus(CorpusProtocol):
        def __init__(self, root: Path,
                     summaries_file: str | None = None,
                     cross_links_file: str | None = None):
          - Walks root for *.md files (configurable glob)
          - Reads with encoding="utf-8"
          - Category inferred from first path segment under root
          - Optional summaries.json and cross_links.json loaded
          - Caches in memory; constructor parameter cache=False
            disables caching for tests
          - Uses _validate_file_path from attune.security if
            importable, else does local realpath check inside
            root
        name property returns "directory:{root.name}"
        version property returns hash of all file mtimes
    </file>
    <file path="packages/attune-rag/tests/unit/test_corpus_directory.py">
      Tests:
        - load from a tmp_path dir with 5 .md files works
        - summaries.json + cross_links.json loaded when present
        - categories inferred correctly
        - path traversal attempt rejected
        - caching works within a single process
        - name/version properties populated
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_corpus_directory.py -v passes</check>
    <check>DirectoryCorpus(Path("some-dir")) enumerates only .md files by default</check>
    <check>No import-time dep on attune-help</check>
  </validation>

  <risks>
    <risk severity="medium">
      Path traversal when DirectoryCorpus is given a
      user-supplied root. Mitigation: resolve root to real
      path and reject entries whose resolved path is not a
      descendant. Follow the established
      _validate_file_path pattern.
    </risk>
  </risks>
</task>

<task id="1.3" name="corpus-attune-help">
  <objective>
    Ship AttuneHelpCorpus as a thin adapter that locates the
    bundled attune-help templates directory via
    importlib.resources and delegates to DirectoryCorpus.
    Available only when the [attune-help] extra is installed.
  </objective>

  <context>
    <existing-code path="attune-help package">
      Ships 633 templates at attune_help/templates/ with
      summaries.json and cross_links.json siblings.
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/corpus/attune_help.py">
      class AttuneHelpCorpus(CorpusProtocol):
        def __init__(self):
          try:
            from importlib.resources import files
            root = files("attune_help").joinpath("templates")
          except (ImportError, ModuleNotFoundError):
            raise RuntimeError(
              "AttuneHelpCorpus requires the [attune-help] "
              "extra: pip install 'attune-rag[attune-help]'"
            )
          self._inner = DirectoryCorpus(
            Path(str(root)),
            summaries_file="summaries.json",
            cross_links_file="cross_links.json",
          )
        name property returns "attune-help"
        version property returns attune_help.__version__
        entries/get delegate to self._inner
    </file>
    <file path="packages/attune-rag/tests/unit/test_corpus_attune_help.py">
      pytest.importorskip("attune_help")  # per CLAUDE.md lesson
      Tests:
        - enumerates >=500 entries
        - version matches attune_help.__version__
        - get() returns by template path
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_corpus_attune_help.py -v passes when attune-help is installed</check>
    <check>Tests SKIP (not fail) when attune-help is absent</check>
    <check>Importing attune_rag without [attune-help] extra does NOT fail (corpus is lazy)</check>
  </validation>

  <risks>
    <risk severity="medium">
      importlib.resources.files() API differences across
      Python versions. Mitigation: target 3.10+ only and
      add smoke test on minimum Python.
    </risk>
    <risk severity="medium">
      attune-help template path scheme may shift.
      Mitigation: pin >=0.5.1,<0.6 in [attune-help] extra.
    </risk>
  </risks>
</task>

<task id="1.4" name="keyword-retriever">
  <objective>
    Implement KeywordRetriever as a CorpusProtocol consumer
    — works with any corpus, not just attune-help. Returns
    ranked RetrievalEntry + score pairs.
  </objective>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/retrieval.py">
      class RetrieverProtocol(Protocol):
        def retrieve(self, query: str, corpus: CorpusProtocol,
                     k: int = 3) -> list[RetrievalHit]: ...

      @dataclass(frozen=True) RetrievalHit:
        entry: RetrievalEntry
        score: float
        match_reason: str  # short explanation for debugging

      class KeywordRetriever(RetrieverProtocol):
        # Tunable class attrs (benchmark can sweep):
        PATH_WEIGHT = 2.0
        SUMMARY_WEIGHT = 1.5
        CONTENT_WEIGHT = 1.0
        RELATED_WEIGHT = 0.5
        MIN_SCORE = 2.0
        STOPWORDS = frozenset({"a", "an", "the", "how", "do",
                               "i", "to", "with", ...})

        - Tokenizes query (lowercase, strip punctuation,
          drop stopwords)
        - Iterates corpus.entries()
        - Scores per weights above; related score uses
          entry.related (cross-links) -> look up via
          corpus.get(related_path).summary
        - Returns top-k hits where score >= MIN_SCORE
        - Deterministic: ties broken by entry.path alpha
    </file>
    <file path="packages/attune-rag/tests/unit/test_retrieval.py">
      Uses an in-memory fake CorpusProtocol for determinism
      (not attune-help) so tests don't depend on optional extra.
      Tests:
        - exact match ("security audit" -> security-audit)
        - synonym match via summary
        - below-threshold returns []
        - deterministic tie-breaking
        - k bounds respected
        - empty query raises ValueError
        - tunable weights actually affect ranking
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_retrieval.py -v passes without [attune-help] extra installed</check>
    <check>Retriever is deterministic (3 runs, same output)</check>
    <check>Weight attrs are class-level so benchmark can override</check>
  </validation>

  <risks>
    <risk severity="medium">
      Weights hand-tuned; benchmark (2.4) may require
      adjustment. Mitigation: class attrs, not hard-coded.
    </risk>
  </risks>
</task>

<task id="1.5" name="provenance-and-prompts">
  <objective>
    Implement the provenance record that travels with every
    RagResult, and the augmented prompt template that clearly
    separates retrieved context from the user query.
  </objective>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/provenance.py">
      @dataclass(frozen=True) CitationRecord:
        query: str
        hits: tuple[CitedSource, ...]  # tuple for hashability
        retrieved_at: datetime
        retriever_name: str  # "KeywordRetriever v0.1.0"

      @dataclass(frozen=True) CitedSource:
        template_path: str
        category: str
        score: float
        excerpt: str | None  # optional first 200 chars

      def format_citations_markdown(record: CitationRecord,
                                    base_url: str | None = None) -> str:
        Render as "## Sources\n- [path](base_url/path) -
        category (score 0.85)\n..."
        Empty hits => "No grounding sources available."
    </file>
    <file path="packages/attune-rag/src/attune_rag/prompts.py">
      AUGMENTED_TEMPLATE = '''### CONTEXT (from attune help docs)

      {context}

      ### USER REQUEST

      {query}

      ### INSTRUCTION

      Answer the user's request using the context above. If
      the context does not contain the answer, say so
      clearly; do not invent attune APIs, workflow names, or
      CLI commands. When referencing specific patterns, note
      which source file they came from.'''

      def build_augmented_prompt(query: str, context: str) -> str
      def join_context(hits: list[RetrievalHit],
                       corpus: CorpusIndex,
                       max_chars: int = 20_000) -> str
    </file>
    <file path="packages/attune-rag/tests/unit/test_provenance.py">
      Tests: empty citation, single, multiple, markdown
      format, deterministic ordering, hashability (since
      frozen).
    </file>
    <file path="packages/attune-rag/tests/unit/test_prompts.py">
      Tests: prompt contains both sections, truncation at
      max_chars, join preserves source boundaries with a
      separator line.
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_provenance.py -v passes</check>
    <check>pytest packages/attune-rag/tests/unit/test_prompts.py -v passes</check>
    <check>format_citations_markdown output is valid markdown (passes markdownlint)</check>
  </validation>

  <risks>
    <risk severity="low">
      Prompt injection via retrieved content. Mitigation:
      explicit "### CONTEXT" / "### USER REQUEST" markers
      and instruction that model must not follow instructions
      embedded in context. Low risk since attune-help
      corpus is maintainer-authored.
    </risk>
  </risks>
</task>

<task id="1.6" name="pipeline-orchestrator">
  <objective>
    Wire corpus + retriever + provenance + prompt assembly
    into RagPipeline.run() — corpus-agnostic, LLM-agnostic.
    Returns an augmented prompt string; the consumer feeds
    it to whatever LLM it chooses.
  </objective>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/pipeline.py">
      @dataclass(frozen=True) RagResult:
        augmented_prompt: str
        citation: CitationRecord
        confidence: float
        fallback_used: bool
        elapsed_ms: float

      class RagPipeline:
        def __init__(self,
                     corpus: CorpusProtocol | None = None,
                     retriever: RetrieverProtocol | None = None):
          # If no corpus provided, try AttuneHelpCorpus;
          # on ImportError emit a clear message telling the
          # user to either pass a corpus explicitly or
          # install attune-rag[attune-help].
          self.corpus = corpus or self._default_corpus()
          self.retriever = retriever or KeywordRetriever()

        @staticmethod
        def _default_corpus() -> CorpusProtocol:
          try:
            from .corpus.attune_help import AttuneHelpCorpus
            return AttuneHelpCorpus()
          except (ImportError, ModuleNotFoundError, RuntimeError) as e:
            raise RuntimeError(
              "No corpus provided and AttuneHelpCorpus is "
              "unavailable. Either pass a corpus= (e.g. "
              "DirectoryCorpus) or install "
              "attune-rag[attune-help]."
            ) from e

        def run(self, query: str, k: int = 3) -> RagResult:
          # Timed, logged via structlog
          # On zero hits: fallback prompt tells model there
          # is no grounding context so it must say it
          # doesn't know rather than invent.
    </file>
    <file path="packages/attune-rag/tests/unit/test_pipeline.py">
      Tests:
        - happy path with a fake CorpusProtocol
        - happy path with DirectoryCorpus (tmp_path)
        - no-match -> fallback_used=True
        - elapsed_ms populated
        - accepts injected retriever + corpus
        - default ctor raises helpful error when
          attune-help unavailable
        - one structured log event per run
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_pipeline.py -v passes</check>
    <check>pipeline.run("security audit") returns confidence >= 0.5 (with attune-help corpus)</check>
    <check>pipeline.run("asdfgh") returns fallback_used=True</check>
    <check>Importing attune_rag without any optional extras works; only constructing AttuneHelpCorpus fails</check>
  </validation>

  <risks>
    <risk severity="low">
      Default corpus instantiation at __init__ time pays
      the corpus-load cost even if unused. Mitigation: lazy
      load on first .run() call; cache in instance.
    </risk>
  </risks>
</task>

<task id="1.7" name="provider-adapters">
  <objective>
    Ship thin, optional provider adapters for Claude,
    OpenAI, and Gemini behind extras. Each exposes an async
    generate(prompt: str) -> str method. No provider is
    installed or imported unless its extra is enabled.
  </objective>

  <context>
    <existing-code path="CLAUDE.md lesson">
      Mock a lazy `import X` with `types.ModuleType` +
      `patch.dict("sys.modules")` — the pattern we'll use
      to test adapters without installing their SDKs.
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/providers/__init__.py">
      Exports: LLMProvider (protocol), list_available().
      list_available() introspects which provider modules
      can actually be imported and returns their names.
    </file>
    <file path="packages/attune-rag/src/attune_rag/providers/base.py">
      class LLMProvider(Protocol):
        name: str
        async def generate(self, prompt: str,
                           model: str | None = None,
                           max_tokens: int = 2048) -> str: ...
    </file>
    <file path="packages/attune-rag/src/attune_rag/providers/claude.py">
      class ClaudeProvider(LLMProvider):
        name = "claude"
        DEFAULT_MODEL = "claude-sonnet-4-6"
        def __init__(self, api_key: str | None = None):
          try:
            from anthropic import Anthropic, AsyncAnthropic
          except ImportError as e:
            raise RuntimeError(
              "ClaudeProvider requires 'pip install "
              "attune-rag[claude]'"
            ) from e
          self._client = AsyncAnthropic(api_key=api_key)
        async def generate(self, prompt, model=None,
                           max_tokens=2048) -> str:
          response = await self._client.messages.create(
            model=model or self.DEFAULT_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
          )
          return response.content[0].text
    </file>
    <file path="packages/attune-rag/src/attune_rag/providers/openai.py">
      class OpenAIProvider(LLMProvider):
        name = "openai"
        DEFAULT_MODEL = "gpt-4o"
        Similar structure — lazy import, clear error on
        missing extra, async generate via
        openai.AsyncOpenAI.chat.completions.create.
    </file>
    <file path="packages/attune-rag/src/attune_rag/providers/gemini.py">
      class GeminiProvider(LLMProvider):
        name = "gemini"
        DEFAULT_MODEL = "gemini-1.5-pro"
        Similar — lazy import google.genai, async generate.
    </file>
    <file path="packages/attune-rag/tests/unit/providers/test_claude.py">
      Uses types.ModuleType + patch.dict("sys.modules")
      pattern (CLAUDE.md lesson) to simulate the anthropic
      module. Tests: lazy import error with clear message,
      generate() passes prompt to client, model default
      honored, model override honored.
    </file>
    <file path="packages/attune-rag/tests/unit/providers/test_openai.py">
      Same pattern for openai.
    </file>
    <file path="packages/attune-rag/tests/unit/providers/test_gemini.py">
      Same pattern for google.genai.
    </file>
    <file path="packages/attune-rag/tests/unit/providers/test_list_available.py">
      Tests: returns empty list when no extras installed;
      returns names when extras are importable. Uses sys.modules
      patching to simulate states.
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/providers/ -v passes with all extras installed (dev extra pulls them)</check>
    <check>pytest passes when extras are absent (tests use sys.modules patching, not actual install)</check>
    <check>Importing attune_rag without any [provider] extra does NOT fail</check>
    <check>Constructing ClaudeProvider without anthropic installed raises a clear RuntimeError pointing at the install command</check>
  </validation>

  <risks>
    <risk severity="high">
      Provider SDK APIs shift. Mitigation: adapters are thin
      (~30 lines each). Version-pin SDKs in extras
      conservatively (>=X.Y,<X+1.0). Each adapter has its
      own CI smoke test.
    </risk>
    <risk severity="medium">
      Model names rot (e.g. Gemini's DEFAULT_MODEL).
      Mitigation: callers always pass explicit model in
      production code. Document this in README.
    </risk>
    <risk severity="medium">
      Async vs sync. Some users will want sync.
      Mitigation: v0.1.0 ships async only. Add sync shims
      (`.generate_sync()` wrapping anyio.from_thread.run)
      in v0.2.0 if demand exists.
    </risk>
  </risks>
</task>

<task id="1.8" name="run-and-generate-and-cli">
  <objective>
    Add RagPipeline.run_and_generate(query, provider) as a
    one-line convenience wrapping retrieve + LLM call. Ship
    a tiny CLI `attune-rag query "..."` for debugging
    retrieval (no LLM call by default; --provider flag
    optional).
  </objective>

  <files-to-modify>
    <file path="packages/attune-rag/src/attune_rag/pipeline.py">
      <change location="RagPipeline">
        AFTER: add
        async def run_and_generate(
            self, query: str,
            provider: LLMProvider | str,
            k: int = 3,
            model: str | None = None,
        ) -> tuple[str, RagResult]:
          If provider is a string, resolve to one of the
          built-in adapters by name. Runs retrieval, sends
          augmented_prompt to provider.generate, returns
          (response_text, rag_result). Callers render
          citations with format_citations_markdown as needed.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="packages/attune-rag/src/attune_rag/cli.py">
      Typer CLI with subcommands:
        attune-rag query "how do I run a security audit?"
          -> prints retrieval hits + citations (no LLM)
        attune-rag query "..." --provider claude
          -> retrieves + calls provider + prints response
        attune-rag corpus-info
          -> shows default corpus name, version, entry count
      Entry point: [project.scripts] attune-rag =
      "attune_rag.cli:app"
    </file>
    <file path="packages/attune-rag/tests/unit/test_cli.py">
      Tests with typer.testing.CliRunner:
        - query without provider prints hits
        - query with --provider claude calls mocked adapter
        - corpus-info shows counts
        - query with invalid provider gives clear error
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/unit/test_cli.py -v passes</check>
    <check>attune-rag query "security audit" works from command line</check>
    <check>attune-rag --help lists query and corpus-info</check>
    <check>run_and_generate integration test end-to-end with mocked provider passes</check>
  </validation>

  <risks>
    <risk severity="low">
      CLI binary name collision with another PyPI package.
      Mitigation: confirm availability during publish. The
      package is "attune-rag" so CLI name "attune-rag" is
      natural.
    </risk>
  </risks>
</task>

---

## Phase 2: `attune-ai` 6.0.0 consumer

<task id="2.1" name="attune-ai-depend-on-attune-rag">
  <objective>
    Add attune-rag>=0.1.0 as a core dep of attune-ai and
    configure dev resolution via workspace.
  </objective>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="dependencies">
        AFTER: add "attune-rag>=0.1.0,<0.2".
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv sync --extra dev --extra developer succeeds</check>
    <check>uv run python -c "from attune_rag import RagPipeline"</check>
    <check>pip-audit passes (or see known-issue list)</check>
  </validation>

  <risks>
    <risk severity="medium">
      attune-rag not yet published to PyPI when attune-ai
      is installed from source. Mitigation: for dev install,
      uv resolves from workspace. For release, attune-rag
      must publish FIRST (see task 4.4 ordering).
    </risk>
  </risks>
</task>

<task id="2.2" name="rag-code-gen-workflow">
  <objective>
    Create the rag_code_gen workflow in attune-ai that calls
    attune-rag's pipeline, sends the augmented prompt to
    Claude Agent SDK, and returns a WorkflowResult with the
    generated code plus markdown citations.
  </objective>

  <context>
    <existing-code path="src/attune/workflows/security_audit.py">
      Reference BaseWorkflow pattern. Per CLAUDE.md lesson:
      use collect_agent_output() from agent_sdk_adapter.py
      to capture both AssistantMessage TextBlocks and
      ResultMessage.result (which is often None).
    </existing-code>
  </context>

  <files-to-create>
    <file path="src/attune/workflows/rag_code_gen.py">
      class RagCodeGenWorkflow(BaseWorkflow):
        name = "rag-code-gen"
        stages = ["retrieve", "generate"]
        tier_map = {"retrieve": ModelTier.CHEAP,
                    "generate": ModelTier.CAPABLE}

        _pipeline: RagPipeline = None  # lazy init

        async def execute(self, **kwargs) -> WorkflowResult:
          query = kwargs["query"]
          if self._pipeline is None:
            self._pipeline = RagPipeline()
          rag_result = self._pipeline.run(query)

          response = await query_agent_sdk(
            rag_result.augmented_prompt,
            tier=ModelTier.CAPABLE,
          )
          generated = collect_agent_output(response)

          citations_md = format_citations_markdown(
            rag_result.citation,
            base_url="https://github.com/Smart-AI-Memory/attune-help/blob/main/src/attune_help/templates",
          )
          output = f"{generated}\n\n{citations_md}"

          return WorkflowResult(
            success=True,
            stages=[...],
            metadata={
              "citation": asdict(rag_result.citation),
              "fallback_used": rag_result.fallback_used,
              "confidence": rag_result.confidence,
            },
            findings=[output],
            started_at=...,
            completed_at=...,
            total_duration_ms=...,
          )
    </file>
    <file path="tests/integration/rag/__init__.py">
      Empty marker.
    </file>
    <file path="tests/integration/rag/test_rag_workflow.py">
      E2E with Claude Agent SDK mocked:
        - execute returns WorkflowResult with success=True
        - metadata.citation has expected feature hints
        - output contains "## Sources" block
        - fallback path used when query is out-of-scope
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/__init__.py">
      <change location="_DEFAULT_WORKFLOW_NAMES">
        AFTER: register RagCodeGenWorkflow.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/integration/rag/test_rag_workflow.py -v passes</check>
    <check>attune workflow list includes rag-code-gen</check>
    <check>attune workflow run rag-code-gen --input '{"query":"how do I run a security audit?"}' returns result with citations</check>
  </validation>

  <risks>
    <risk severity="medium">
      Workflow registry count assertions exist in multiple
      test files (CLAUDE.md lesson). Mitigation: grep for
      _DEFAULT_WORKFLOW_NAMES count and _SDK_WORKFLOW_MAP
      count assertions; update in same commit.
    </risk>
    <risk severity="medium">
      ResultMessage.result is often None. Mitigation: use
      collect_agent_output() per the existing lesson.
    </risk>
  </risks>
</task>

<task id="2.3" name="mcp-tool-rag-knowledge-query">
  <objective>
    Register the rag_knowledge_query MCP tool in attune-ai
    so Claude Code and other MCP clients can query the
    corpus without running a full workflow.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/tool_schemas.py">
      Schema lives in get_workflow_tools() or
      get_memory_tools(). Tool count is asserted in
      tests/unit/test_mcp_memory_tools.py — bump it.
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/mcp/tool_schemas.py">
      <change location="get_workflow_tools">
        AFTER: append rag_knowledge_query schema.
        Inputs: query (str, required), k (int, default 3).
        Description notes: returns JSON with hits,
        augmented_prompt, confidence, fallback_used.
      </change>
    </file>
    <file path="src/attune/mcp/workflow_handlers.py">
      <change location="dispatch table + handlers">
        AFTER: add _run_rag_knowledge_query(arguments).
        Validate k in [1,10]. Construct lazy singleton
        RagPipeline. Return TextContent with JSON body.
      </change>
    </file>
    <file path="tests/unit/test_mcp_memory_tools.py">
      <change location="tool count assertion">
        AFTER: bump by 1.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="tests/unit/rag/test_mcp_tool.py">
      Tests: schema registration, happy-path dispatch,
      k-bounds validation, no-match result shape.
    </file>
  </files-to-create>

  <validation>
    <check>pytest tests/unit/rag/test_mcp_tool.py -v passes</check>
    <check>pytest tests/unit/test_mcp_memory_tools.py -v passes</check>
    <check>MCP server lists rag_knowledge_query</check>
  </validation>

  <risks>
    <risk severity="low">
      Single RagPipeline instance shared across MCP
      requests. Mitigation: CorpusIndex is read-only; no
      mutation.
    </risk>
  </risks>
</task>

<task id="2.4" name="golden-query-benchmark">
  <objective>
    Build the benchmark harness that gates whether we invest
    in embeddings. Seeds the dataset with 15+ golden queries
    spanning direct asks, synonyms, out-of-scope, and multi-
    feature asks.
  </objective>

  <files-to-create>
    <file path="packages/attune-rag/tests/golden/queries.yaml">
      Each entry:
        id: gq-001
        query: "how do I run a security audit?"
        expected_top_feature: "security-audit"
        expected_in_top_3: ["quickstarts/security-audit.md"]
        difficulty: easy | medium | hard
        embedding_only: false
      Cover: 5 easy, 5 medium, 5 hard.
    </file>
    <file path="packages/attune-rag/tests/golden/test_golden.py">
      Parametrized pytest that loads queries.yaml and asserts
      each expected_top_feature appears in top 3 hits.
    </file>
    <file path="packages/attune-rag/src/attune_rag/benchmark.py">
      Runnable: python -m attune_rag.benchmark
      Prints:
        Retriever: KeywordRetriever v0.1.0
        Corpus:    633 templates
        Precision@1: 0.80 (12/15)
        Recall@3:    0.93 (14/15)
        Mean latency: 4.2ms
      Exit 1 if precision@1 < 0.70 (configurable via
      --min-precision) so CI can gate.
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-rag/tests/golden/ -v passes at baseline</check>
    <check>python -m attune_rag.benchmark exits 0 at baseline</check>
    <check>Benchmark is deterministic across runs</check>
  </validation>

  <risks>
    <risk severity="medium">
      Hand-authored queries biased toward the retriever we
      built. Mitigation: at least 5 queries labeled "hard"
      with non-obvious wording (synonyms, typos). Anyone
      adding queries must mark difficulty honestly.
    </risk>
  </risks>
</task>

<task id="2.5" name="embeddings-gate-decision">
  <objective>
    Decision point, not implementation. If keyword retrieval
    hits precision@1 >= 0.85 and recall@3 >= 0.90 on the
    golden set, DO NOT add embeddings. Otherwise spike a
    hosted-embeddings prototype (Voyage, OpenAI, Anthropic
    when available) and re-benchmark.
  </objective>

  <files-to-create>
    <file path="docs/rag/embeddings-decision-2026-04-17.md">
      Written 2026-04-17. RESOLVED.

      Baseline: KeywordRetriever hits 53.33% P@1 / 60% R@3
      on 15 golden queries. Easy+medium pass; all 6 hard
      queries fail with the same pattern — lesson/error files
      with query keywords in the filename outrank the concept
      files that actually answer.

      Decision: sequence keyword tuning first (v0.1.x patch),
      then fastembed (local ONNX embeddings, ~35MB) as
      fallback in v0.2.0 if the gate isn't met. NOT
      sentence-transformers (420MB, fails <50MB gate). NOT
      hosted embeddings for v0.2.0 (keeps architectural posture
      of local-corpus / local-retrieval).

      Clarifies that the "sentence-transformers removed" lesson
      was about semantic CACHING (0.4% ROI on unique prompts),
      not RAG RETRIEVAL. Different problems, different ROI
      profiles. Keyword tuning and fastembed are both
      defensible in light of the clarified lesson.
    </file>
  </files-to-create>

  <validation>
    <check>Decision doc exists and is linked from this plan (RESOLVED 2026-04-17)</check>
    <check>Follow-up task filed: v0.1.x category-biased keyword tuning</check>
    <check>Follow-up task filed: v0.2.0 fastembed EmbeddingRetriever (conditional)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Sunk-cost bias after spiking embeddings. Mitigation:
      write the gate criteria before running comparison;
      commit them in the doc before measuring.
    </risk>
  </risks>
</task>

---

## Phase 3: `attune-author` 0.4.0 consumer

<task id="3.1" name="attune-author-depend-on-attune-rag">
  <objective>
    Add attune-rag>=0.1.0 as an optional dependency of
    attune-author, exposed via an extra (e.g.
    attune-author[rag]). If the extra is not installed,
    attune-author falls back to the pre-RAG generation path
    with a warning.
  </objective>

  <files-to-modify>
    <file path="packages/attune-author/pyproject.toml">
      <change location="optional-dependencies">
        AFTER: add `rag = ["attune-rag>=0.1.0,<0.2"]`.
        Keep attune-rag OUT of core deps to preserve
        lightweight install.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>uv sync --extra rag succeeds</check>
    <check>uv sync without --extra rag still resolves cleanly</check>
    <check>Import attune_rag only inside attune_author.rag_hook module (not at package import time)</check>
  </validation>

  <risks>
    <risk severity="low">
      Optional-extra dep is invisible at runtime until
      imported. Mitigation: rag_hook.py uses the MetaPathFinder
      pattern from CLAUDE.md to verify the boundary stays clean.
    </risk>
  </risks>
</task>

<task id="3.2" name="author-rag-hook">
  <objective>
    Wire RAG into `attune-author generate` with the middle-
    ground UX: on by default when attune-rag is installed,
    opt-out via --no-rag flag or ATTUNE_AUTHOR_RAG=0 env
    override. Log a one-line notice the first time RAG fires
    per session pointing at docs.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/rag_hook.py">
      def rag_enabled() -> bool:
        if os.environ.get("ATTUNE_AUTHOR_RAG") == "0":
          return False
        try:
          import attune_rag  # noqa: F401
        except ImportError:
          return False
        return True

      def ground_generation(query: str, k: int = 3) -> str | None:
        if not rag_enabled():
          return None
        from attune_rag import RagPipeline
        pipeline = RagPipeline()
        result = pipeline.run(query, k=k)
        if result.fallback_used:
          return None
        return result.augmented_prompt
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="packages/attune-author/src/attune_author/cli.py">
      <change location="generate subcommand">
        AFTER: add --no-rag bool flag (default False).
        If not --no-rag and rag_enabled(): call
        ground_generation() and pass the augmented prompt to
        the generator. If rag_hook returns None (fallback or
        disabled), proceed with the original path.
      </change>
    </file>
    <file path="packages/attune-author/src/attune_author/generator.py">
      <change location="generate_feature_templates">
        AFTER: accept optional augmented_prompt parameter.
        When provided, use it instead of the bare prompt.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path="packages/attune-author/tests/unit/test_rag_hook.py">
      Tests:
        - rag_enabled() false when ATTUNE_AUTHOR_RAG=0
        - rag_enabled() false when attune_rag not installed
          (simulate via sys.modules patch per CLAUDE.md lesson)
        - --no-rag flag disables even when env allows
        - hook returns None on fallback (out-of-scope query)
        - hook returns augmented prompt on match
    </file>
  </files-to-create>

  <validation>
    <check>pytest packages/attune-author/tests/unit/test_rag_hook.py -v passes</check>
    <check>attune-author generate security-audit uses RAG (check log output)</check>
    <check>attune-author generate security-audit --no-rag skips RAG</check>
    <check>ATTUNE_AUTHOR_RAG=0 attune-author generate ... skips RAG</check>
  </validation>

  <risks>
    <risk severity="high">
      Determinism: golden/regression tests in attune-author
      may flake if RAG is on by default and retrieval order
      shifts. Mitigation: CI tests run with ATTUNE_AUTHOR_RAG=0
      by default. Separate CI lane runs with RAG enabled and
      accepts softer assertions (contains vs equals).
    </risk>
    <risk severity="medium">
      Output format change breaks scripts parsing generator
      output. Mitigation: default RAG output stays visually
      compatible; citations appended in a labeled section
      that scripts can skip.
    </risk>
    <risk severity="medium">
      Latency tax on batch generate (regen of 24 features =
      24x retrieval cost). Mitigation: RagPipeline caches
      corpus globally; keyword retrieval is ~4ms per query.
      Total overhead on batch: ~100ms, acceptable.
    </risk>
  </risks>
</task>

<task id="3.3" name="author-cli-docs-update">
  <objective>
    Document the new flag, env override, and on-by-default
    behavior in attune-author's README and --help output.
  </objective>

  <files-to-modify>
    <file path="packages/attune-author/README.md">
      <change location="CLI usage section">
        AFTER: document --no-rag, ATTUNE_AUTHOR_RAG=0, and
        how grounding changes generated output.
      </change>
    </file>
    <file path="packages/attune-author/src/attune_author/cli.py">
      <change location="generate subcommand --help">
        AFTER: flag help text describes the default and
        points at attune-ai docs for the RAG explainer.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>attune-author generate --help shows --no-rag</check>
    <check>README has a Grounded Generation section</check>
  </validation>

  <risks>
    <risk severity="low">
      README drift between packages. Mitigation: single
      source of truth for the RAG explainer lives in
      attune-ai docs; attune-author README links to it.
    </risk>
  </risks>
</task>

---

## Phase 4: Release coordination

<task id="4.1" name="feedback-integration-attune-ai">
  <objective>
    Wire the attune-ai rag_code_gen workflow into existing
    help/feedback.py so every RAG invocation can be rated
    good/bad by the user and aggregated into template
    confidence over time.
  </objective>

  <context>
    <existing-code path="src/attune/help/feedback.py">
      record_template_feedback(template_id, verdict) where
      verdict is "good" or "bad". Atomic writes. Returns
      None. get_template_confidence(template_id) returns
      good / (good + bad).
    </existing-code>
  </context>

  <files-to-modify>
    <file path="src/attune/workflows/rag_code_gen.py">
      <change location="execute()">
        AFTER: if kwargs has feedback in ("good", "bad"),
        iterate over rag_result.citation.hits and call
        record_template_feedback(hit.template_path, feedback)
        for each. No silent implicit ratings.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Running rag-code-gen with feedback="good" increments good counts in feedback.json</check>
    <check>Running without feedback leaves feedback.json untouched</check>
    <check>Confidence for a never-seen template is 0.5 (neutral prior)</check>
  </validation>

  <risks>
    <risk severity="low">
      Concurrent writes (existing lesson: atomic in
      feedback.py already).
    </risk>
  </risks>
</task>

<task id="4.2" name="skill-and-website">
  <objective>
    Add Claude Code skill entry for rag-code-gen. Update
    attune-ai's website with a RAG feature page. Update the
    README's top-level feature list. Add blog post placeholder.
  </objective>

  <files-to-create>
    <file path="plugin/skills/rag-code-gen/SKILL.md">
      Frontmatter: name, description (<250 chars per
      CLAUDE.md rule), user-invocable: true, trigger phrases
      like "grounded code", "ground this in attune", "use
      attune docs". Body: when to route, what citations look
      like.
    </file>
    <file path=".agents/skills/rag-code-gen/SKILL.md">
      Mirror of plugin/skills version, synced via
      scripts/sync_agents_skills.py.
    </file>
    <file path="docs/rag/index.md">
      User-facing doc: what RAG does, how to invoke via
      workflow/MCP/skill, sample citation output, feedback
      kwarg.
    </file>
    <file path="plugin/help/generated/concepts/tool-rag-code-gen.md">
      Concept doc generated via attune-author regenerate
      flow.
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="plugin/.claude-plugin/plugin.json">
      <change location="skills array">
        AFTER: register rag-code-gen skill.
      </change>
    </file>
    <file path="README.md">
      <change location="features list">
        AFTER: add grounded code generation bullet with link
        to docs/rag/index.md. Update badges only if stable
        counts (tests, coverage) shift materially.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Skill description len <250 chars</check>
    <check>pytest tests/unit/plugins/test_plugin_reference_validation.py -v passes</check>
    <check>pytest -k skill_synced -v passes</check>
    <check>README renders correctly on GitHub (absolute URLs per lesson)</check>
  </validation>

  <risks>
    <risk severity="low">
      Skill frontmatter field drift. Mitigation: use only
      allowlisted fields per CLAUDE.md.
    </risk>
    <risk severity="low">
      Website changes. Website edits live outside this repo;
      scope is "add placeholder / stub" and reference the
      website repo path for the human to complete.
    </risk>
  </risks>
</task>

<task id="4.3" name="version-bumps-across-packages">
  <objective>
    Bump versions: attune-rag 0.0.0 -> 0.1.0 (initial),
    attune-ai <current> -> 6.0.0, attune-author 0.3.9 ->
    0.4.0. Update all tracked files per the CLAUDE.md rule
    that test_all_versions_match enforces. Add CHANGELOG
    entries on attune-ai and attune-author.
  </objective>

  <context>
    <existing-code path="CLAUDE.md">
      Version bumps must update: pyproject.toml,
      plugin/.claude-plugin/plugin.json,
      plugin/.claude-plugin/marketplace.json (two fields),
      plugin/core/__init__.py,
      .claude-plugin/marketplace.json, .claude/CLAUDE.md
      (header + footer).
    </existing-code>
  </context>

  <files-to-modify>
    <file path="pyproject.toml">
      <change location="version">AFTER: 6.0.0</change>
    </file>
    <file path="plugin/.claude-plugin/plugin.json">
      <change location="version">AFTER: 6.0.0</change>
    </file>
    <file path="plugin/.claude-plugin/marketplace.json">
      <change location="metadata.version AND plugins[0].version">
        AFTER: 6.0.0 in both.
      </change>
    </file>
    <file path="plugin/core/__init__.py">
      <change location="__version__">AFTER: 6.0.0</change>
    </file>
    <file path=".claude-plugin/marketplace.json">
      <change location="root version">AFTER: 6.0.0</change>
    </file>
    <file path=".claude/CLAUDE.md">
      <change location="header + footer">AFTER: 6.0.0</change>
    </file>
    <file path="CHANGELOG.md">
      <change location="prepend">
        AFTER: "## [6.0.0] - 2026-MM-DD - Grounded Code
        Generation" with feature summary, new attune-rag
        dep, migration note (no-op for non-RAG users),
        breaking-change disclosure (none expected — this is
        additive; 6.0.0 is communicative not technical).
      </change>
    </file>
    <file path="packages/attune-author/pyproject.toml">
      <change location="version">AFTER: 0.4.0</change>
    </file>
    <file path="packages/attune-author/CHANGELOG.md">
      <change location="prepend">
        AFTER: "## [0.4.0] - ... - Optional RAG grounding".
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>pytest tests/unit/test_plugin_config_validation.py::test_all_versions_match -v passes</check>
    <check>uv lock --check passes</check>
    <check>grep -r "&lt;old_version&gt;" . returns no results outside CHANGELOG history</check>
  </validation>

  <risks>
    <risk severity="medium">
      Breaking-change disclosure on 6.0.0. This IS a major
      bump even though additive — users should know why.
      Mitigation: CHANGELOG spells out "major bump chosen
      for communicative weight; no API removals or incompat
      changes."
    </risk>
  </risks>
</task>

<task id="4.4" name="coordinated-publish">
  <objective>
    Publish in the correct order so version constraints
    resolve: attune-rag first, then attune-ai, then
    attune-author. Use GitHub Actions trusted publishing
    (CLAUDE.md lesson about local twine 504s).
  </objective>

  <files-to-modify>
    <file path=".github/workflows/publish-pypi.yml">
      <change location="workflow">
        AFTER: ensure workflow supports publishing from
        packages/attune-rag/. May need a matrix or a new
        workflow file. Preserve the "pypi" environment
        manual approval gate per CLAUDE.md lesson.
      </change>
    </file>
  </files-to-modify>

  <files-to-create>
    <file path=".github/workflows/publish-attune-rag.yml">
      Separate workflow if single-workflow matrix is too
      complex. Trusted publishing via OIDC. Uses the same
      "pypi" environment for manual approval.
    </file>
  </files-to-create>

  <validation>
    <check>attune-rag 0.1.0 appears on pypi.org</check>
    <check>attune-ai 6.0.0 resolves attune-rag>=0.1.0 from PyPI (not workspace)</check>
    <check>attune-ai 6.0.0 appears on pypi.org</check>
    <check>attune-author 0.4.0 appears on pypi.org with optional [rag] extra</check>
    <check>pip install 'attune-ai[developer]' includes attune-rag transitively</check>
    <check>pip install attune-author does NOT install attune-rag (optional)</check>
  </validation>

  <risks>
    <risk severity="high">
      Ordering: if attune-ai publishes first, users can't
      install it (attune-rag 0.1.0 missing from PyPI).
      Mitigation: publish attune-rag first, verify on PyPI,
      THEN publish attune-ai. Coordinated manual approval.
    </risk>
    <risk severity="medium">
      Trusted publishing environment gates each publish.
      Expect to click "Approve" 3 times (CLAUDE.md lesson
      about "pypi environment requires manual approval").
    </risk>
  </risks>
</task>

---

## Out of Scope / Deferred

- Re-ranker (cross-encoder): deferred until embeddings
  decision is resolved.
- PromptMixin integration across all attune-ai workflows:
  follow-up spec once dedicated RAG workflow is stable.
- Fine-tuning / RLHF loop on feedback data: separate spec.
- attune-help changes: none in v1. If corpus loading exposes
  a need for richer metadata (canonical feature names per
  template), open a separate spec on attune-help.
- Embeddings in attune-rag: gated on benchmark outcome
  (task 2.5).

---

## Approved Follow-up Work

### attune-help corpus metadata enrichment (approved 2026-04-17)

**Decision:** yes — add corpus-level metadata to a future
attune-help minor (targeting 0.6.0). Unblocks attune-rag
0.2.0's schema adapter and significantly improves retrieval
quality.

**Scope (separate spec when we get to it):**

- Add a **path-keyed summaries** schema alongside (or
  replacing) the current feature-keyed
  `summaries.json`. Each template gets a
  one-line summary retrievable by its exact path.
- Publish a **canonical feature map** linking template paths
  to the feature they describe (e.g.
  `"concepts/tool-security-audit.md" -> "security-audit"`).
  Lets retrievers correlate paths to high-level features
  without string-munging.
- Add **difficulty tags** (`"beginner" | "intermediate" |
  "advanced"`) per template so retrievers can bias toward
  the audience the user asked about.
- Restructure **cross-links** to be path-keyed consistently,
  or add a `by_path` lookup index alongside the current
  short-ID-keyed structure.

**Why it matters:** Unblocks the "v0.1.0 note on sidecars"
gap in `AttuneHelpCorpus` — today we load templates without
summaries/related because the schemas don't match. Once
attune-help ships path-keyed schemas, `AttuneHelpCorpus` can
expose `RetrievalEntry.summary`, `.related`, and metadata
like `difficulty`, lifting the `KeywordRetriever`'s
`SUMMARY_WEIGHT` and `RELATED_WEIGHT` paths from dead weight
to real retrieval signal.

**Ordering:** No earlier than attune-rag 0.2.0 planning.
Start as a separate spec in the attune-help repo; don't
couple it to this spec's merge.

---

## Open Questions

1. Should `confidence_from_history` be exposed in the MCP
   tool response? Start model-only; surface to end users
   only if feedback data shows it improves trust.
2. How do we avoid retrieval feedback loops where bad
   generations get marked "bad" and the same template is
   then under-retrieved, hiding the real root cause
   (retriever tuning)? Candidate mitigation: separate
   "retrieval was correct" vs "generation was good"
   feedback axes.
3. Sync vs async in provider adapters. v0.1.0 ships async
   only; watch for user demand before adding sync shims.
4. Telemetry for external users of attune-rag. Do we want
   anonymous retrieval metrics (hit count, fallback rate)?
   Opt-in only; default off. Separate spec if we pursue.
