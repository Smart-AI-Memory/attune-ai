# RAG Implementation Plan: Grounding LLM Code Generation

**Version:** 1.0
**Status:** Planning

## 1. Executive Summary

This document outlines the plan to construct a Retrieval-Augmented Generation (RAG) system that leverages the existing `.help` content as a verifiable knowledge base. The goal is to actively guide LLM code generation, reduce hallucinations, and increase the accuracy and reliability of AI-written code within the `attune-ai` ecosystem.

## 2. Phases

### Phase 1: Foundational RAG Pipeline (1-2 weeks)

This phase focuses on building the minimum viable product: a pipeline that can resolve a user's query to a feature, retrieve the relevant help content, and inject it into the LLM prompt.

**Tasks:**

1.  **Create RAG Core Module:**
    *   Create a new directory: `src/attune/rag/`
    *   Create a new file: `src/attune/rag/pipeline.py` to house the main orchestration logic.

2.  **Implement Topic Resolution:**
    *   In `src/attune/rag/pipeline.py`, create a `resolve_topic(query: str, manifest: FeatureManifest) -> str | None` function.
    *   This function will take a user query and the loaded `features.yaml` manifest.
    *   It will use a simple keyword-matching algorithm against feature names, descriptions, and tags to find the most relevant feature.

3.  **Implement Content Retrieval:**
    *   Create a `retrieve_content(feature_name: str, help_dir: Path) -> str` function.
    *   This function will read the key help files for the given feature from the `plugin/help/generated/` directory (e.g., `concepts/tool-{feature_name}.md`, `quickstarts/{feature_name}.md`).
    *   It will concatenate the content of these files into a single string.

4.  **Implement Context Assembly & Prompting:**
    *   Create a `build_augmented_prompt(query: str, context: str) -> str` function.
    *   This will use a new prompt template that clearly separates the retrieved context from the user's original query.

5.  **Integrate into a Workflow:**
    *   Create a new workflow `src/attune/workflows/rag_code_gen.py`.
    *   This workflow will take a user's coding request, execute the RAG pipeline, and send the augmented prompt to the LLM to generate the code.

### Phase 2: Advanced Retrieval & Caching (2-3 weeks)

This phase enhances the pipeline's accuracy and performance with more sophisticated retrieval techniques.

**Tasks:**

1.  **Implement Embedding-Based Search:**
    *   Integrate a sentence-transformer library (e.g., `sentence-transformers`).
    *   Create a script `scripts/generate_help_embeddings.py` that:
        *   Reads all generated help files.
        *   Chunks them into meaningful sections (e.g., by paragraph or markdown section).
        *   Generates embeddings for each chunk and saves them to a file (e.g., `plugin/help/generated/embeddings.pkl`).
    *   Modify `resolve_topic` and `retrieve_content` to use vector similarity search instead of keyword matching for more accurate retrieval.

2.  **Implement Re-ranking:**
    *   After the initial retrieval of the top-k chunks, use a lightweight cross-encoder model to re-rank them for relevance to the specific user query. This improves the quality of the context provided to the LLM.

3.  **Add a Caching Layer:**
    *   In `src/attune/rag/pipeline.py`, add an in-memory cache (`lru_cache`) for the RAG pipeline results to speed up responses for repeated or similar queries.

### Phase 3: User Feedback & Verification (1 week)

This phase focuses on building user trust and creating a feedback loop for continuous improvement.

**Tasks:**

1.  **Implement Source Attribution:**
    *   Modify the `rag_code_gen` workflow to keep track of which help documents were used as context.
    *   When displaying the generated code, include a list of the source files (e.g., "Generated using context from: `quickstarts/security-audit.md`").

2.  **Create a Feedback Mechanism:**
    *   After code is generated, prompt the user with a simple feedback request (e.g., "Was this code helpful? 👍 / 👎").
    *   Store this feedback along with the query, retrieved context, and generated code in a structured log file (e.g., `logs/rag_feedback.jsonl`). This data will be invaluable for future fine-tuning.

3.  **Build a Verification Test Suite:**
    *   Create a new test file `tests/rag/test_rag_pipeline.py`.
    *   Add a set of "golden" queries and assert that the RAG pipeline retrieves the correct documents and generates accurate code snippets. This will act as a regression test for the RAG system.

## 3. Success Metrics

*   **Code Accuracy:** A measurable reduction in LLM hallucinations, tracked by the verification test suite.
*   **User Trust:** Positive user feedback on the generated code's reliability.
*   **Performance:** RAG pipeline execution time should be under 500ms for cached queries and under 2 seconds for uncached queries.
