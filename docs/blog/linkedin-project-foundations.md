# Your Code Is Already the Documentation

*Part 2 of a series on building living documentation
with Claude Code*

Most teams treat documentation as a separate deliverable.
You write the code, then you write the docs. Two
artifacts, two maintenance burdens, one inevitable drift.

Here's the thing: if you're following standard coding
conventions, your code already contains the
documentation. You just need to treat it that way.

This article walks through five source types that serve
double duty — runtime behavior AND documentation input —
and explains why each one matters for generating a help
system that stays accurate without manual upkeep.

## 1. Google-Style Docstrings

Google's docstring format isn't just a style preference.
It's a structured contract with predictable sections that
a generator can parse.

--- CODE START ---
async def run(
    self,
    task_type: str,
    prompt: str,
    system: str | None = None,
    context: ExecutionContext | None = None,
    **kwargs: Any,
) -> LLMResponse:
    """Execute an LLM call with routing and cost tracking.

    Args:
        task_type: Type of task (e.g., "summarize",
                  "fix_bug"). Used for model tier routing.
        prompt: The user prompt to send to the LLM.
        system: Optional system prompt.
        context: Optional execution context for tracking.
        **kwargs: Additional provider-specific arguments.

    Returns:
        LLMResponse with content, tokens, cost,
        and metadata.
    """
--- CODE END ---

Every Args entry becomes a parameter description in a
reference template. The Returns section becomes the
"what you get back" paragraph. Raises becomes a
troubleshooting entry. The one-line summary becomes the
concept overview.

This isn't theoretical — it's parsing. The structure is
already there. A generator just walks the sections.

**Why it matters:** If your docstrings are unstructured
prose, a generator has to guess what's a parameter and
what's a side note. Google format eliminates the guessing.

## 2. Type Hints

Type hints are documentation you can't lie about. If the
signature says `input_tokens: int` and the function
returns `float`, that's a contract enforced by mypy and
readable by any introspection tool.

--- CODE START ---
def estimate_cost(
    self,
    task_type: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
--- CODE END ---

You don't need to read the body. Three scalars in, a
float out. A generator can produce "Takes a task type
string, input and output token counts, and returns the
estimated cost in dollars" without anyone writing that
sentence.

**Why it matters:** Type hints give generators the
"what" for free. Docstrings provide the "why." Together
they cover both without redundancy.

## 3. YAML Frontmatter in Skills

Claude Code skills use YAML frontmatter — structured
metadata at the top of a markdown file. Name,
description, argument hints, and trigger conditions are
all machine-readable fields.

--- CODE START ---
---
name: planning
description: "High-level development planning —
  features, TDD, architecture review. Triggers on:
  plan, feature, architecture, design, TDD, strategy."
argument-hint: "<what to plan: feature, tdd,
  architecture>"
---
--- CODE END ---

A generator parses this into a registry entry, a help
summary, and a trigger keyword list — from four lines
of YAML.

**Why it matters:** Frontmatter separates metadata from
content. The generator reads the YAML; the user reads
the markdown. Same file, two audiences, zero drift.

## 4. Class Attributes on Workflows

When workflow metadata lives as class-level attributes
rather than constructor parameters or config files, it's
inspectable at import time without instantiation.

--- CODE START ---
class SecurityAuditWorkflow(BaseWorkflow):
    name = "security-audit"
    description = "Agent SDK-powered security audit
        with 4 specialized subagents"
    stages = ["agent-audit"]
    tier_map = {"agent-audit": ModelTier.CAPABLE}
--- CODE END ---

A generator imports the class, reads four attributes,
and produces a workflow card: name, what it does, which
stages run, and which model tier each stage uses. No
YAML parsing, no config file lookup, no runtime
execution.

**Why it matters:** Class attributes are the simplest
form of self-documenting code. They're literal values
on the class object. If someone changes the workflow
name, the docs update because they read from the same
source.

## 5. CLI Help Strings

argparse and typer both attach help text directly to
command definitions. This text is already exposed to
users via --help. A generator can extract it and
reformat it into markdown reference docs.

--- CODE START ---
parser.add_argument(
    "--project", "-p",
    default=".",
    help="Project root directory (default: current
          directory)",
)
parser.add_argument(
    "--json", "-j",
    action="store_true",
    help="Output in JSON format",
)
--- CODE END ---

The help string "Project root directory (default:
current directory)" is the same sentence whether it
appears in terminal output or in a reference template.
Write it once.

**Why it matters:** CLI help strings are the oldest
form of documentation-in-code. The pattern works
because the docs live next to the code they describe —
not in a separate file that someone forgets to update.

## The Underlying Principle

All five source types share one property: **the
metadata is embedded in the code structure, not in a
separate document.** This means:

- A code change automatically changes the documentation
  source
- There's no sync step, no "update the docs" ticket
- The generator reads the same artifact the runtime uses

This is why conventions matter. Google docstrings aren't
just "nice to have" — they're the structural contract
that makes automated documentation possible. Type hints
aren't just for mypy — they're the parameter
descriptions your help system needs. Frontmatter isn't
just file metadata — it's the registry entry for every
skill.

If your team already follows these conventions,
congratulations — you have the raw material for a living
help system. The next article will show how to turn these
sources into templates.

## Try It

Attune AI uses all five source types to generate 557
help templates for itself. Install the Claude Code
plugin and say "tell me more" to see the result:

--- CODE START ---
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
--- CODE END ---

The entire help system runs on your Claude subscription
— no API key required.

This is part 2 of a series on building knowledge bases,
help systems, dynamic assistance, and context-aware
documents with Claude Code and MCP. Follow along if
you want to build something similar.

If you find it useful, a star on the repo helps others
discover the project:
github.com/Smart-AI-Memory/attune-ai

Next up: Template authoring and the 11 template types.
