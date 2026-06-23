---
type: warning
name: rag-grounding-warning
feature: rag-grounding
depth: warning
generated_at: 2026-06-23T22:13:00.800515+00:00
source_hash: 80d56595472151a9fe49e1354a100b17b22eefbeaefb0d01d9a569f85b28b5a4
status: generated
---

# RAG-grounded code generation — retrieves attune context and emits answers with source citations

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'RagCodeGenWorkflow.execute' was never awaited` | `execute` called without `await` | It is a coroutine — `await` it or use `asyncio.run` | high |
| `error` is `"query argument is required"` | `execute` called with an empty/missing `query` | Pass a non-empty `query` | high |
| `RuntimeError: ... needs the attune-rag package ...` | `attune-rag` (a core dependency) is not installed | `pip install attune-rag` | high |
| `error` is `"RAG retrieval failed: ..."` | The pipeline raised (corpus I/O, connection, timeout, bad variant) | Check corpus availability / connectivity; retry | medium |
| `error` is `"k argument must be an integer ..."` | `k` wasn't an int (e.g. `k="bad"`) | Pass an integer `k` | low |
| `error` is `"unknown model ..."` | `model` isn't in `MODEL_REGISTRY` | Use a registered model id, or omit `model` | low |
| `DeprecationWarning` about `cwd=` | Passing the deprecated `cwd` alias | Use `path=` instead | low |

### Risk areas

- **The async call is easy to get wrong.** `execute` is a coroutine;
  forgetting to `await` it is the most common mistake.
- **`attune-rag` must be installed.** It's a core dependency, not an
  optional extra — the workflow can't retrieve without it.
- **Slug vs. feature name.** The CLI slug is `rag-code-gen`; the
  feature/help topic is `rag-grounding`.

### Diagnosis order

1. Confirm you are awaiting: `await workflow.execute(query="...")`.
2. Check `result.success`; if `False`, read `result.error`.
3. If the error mentions attune-rag, `pip install attune-rag`.
4. For a retrieval failure, check corpus availability and connectivity.
5. Inspect `result.metadata["citation"]` to see what was retrieved.
