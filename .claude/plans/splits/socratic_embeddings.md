# Split Plan: socratic/embeddings.py

**File:** src/attune/socratic/embeddings.py
**Lines:** 741
**Created:** 2026-02-20

## Strategy

Convert single file into package directory. Only one
consumer (`socratic/__init__.py`) imports from it.

## New Structure

```text
src/attune/socratic/embeddings/
  __init__.py     # Re-exports public API
  models.py       # EmbeddedGoal, SimilarityResult (~46 lines)
  providers.py    # EmbeddingProvider ABC + 3 implementations (~272 lines)
  store.py        # VectorStore (~213 lines)
  matcher.py      # SemanticGoalMatcher (~151 lines)
```

## Import Impact

Only `socratic/__init__.py` imports from embeddings.
Package `__init__.py` re-exports everything.
Zero import changes needed.
