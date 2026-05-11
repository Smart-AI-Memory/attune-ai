# Tasks — Files API adoption

## Phase 1 — Identify candidates

- [ ] **1.1** Survey current Anthropic call sites:
      `grep -rln "client.messages.create\|messages.create\|messages.stream" src/attune/`
- [ ] **1.2** For each call site, estimate payload size for a
      typical large-repo scan. Identify the top 3 by token
      volume.
- [ ] **1.3** Cross-reference with telemetry data (if any) to
      confirm size estimates with actual run data
- [ ] **1.4** Produce candidate list with priority

## Phase 2 — Pilot one workflow

Pick the highest-leverage candidate (likely `code-review` or
`perf-audit`).

- [ ] **2.1** Sketch the upload → reference → cleanup flow
- [ ] **2.2** Implement upload helper in
      `src/attune/llm/files_api.py` (or wherever the LLM
      provider lives). Handle:
      - file size limits (Anthropic has caps per file/account)
      - retry on upload failure
      - return `file_id`
- [ ] **2.3** Add cleanup helper (`delete_file(file_id)`)
- [ ] **2.4** Migrate the chosen workflow to use the helper
- [ ] **2.5** Test: dry-run on a 100-file repo, confirm
      reduced token count vs inline path
- [ ] **2.6** Add an `--inline-payload` escape hatch flag for
      easy revert

## Phase 3 — Roll out

For each remaining priority workflow from Phase 1:

- [ ] **3.x.1** Migrate to Files API helper
- [ ] **3.x.2** Verify token savings on a representative test
- [ ] **3.x.3** Watch CI for any regression

## Phase 4 — Cleanup story

- [ ] **4.1** Ensure every uploaded `file_id` is paired with a
      cleanup call (`try/finally` or context manager)
- [ ] **4.2** Add a periodic job (cron or post-workflow) that
      lists stale uploads and deletes them
- [ ] **4.3** Add a metric: `files_api_orphan_count` to
      telemetry

## Out of scope

- Multi-modal (image) inputs — separate spec
- Long-term artifact storage — Files API has a TTL, not
  intended for that
- Files API migration for non-attune-ai consumers
  (attune-author, attune-rag have their own concerns)
