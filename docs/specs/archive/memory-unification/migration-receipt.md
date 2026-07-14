# Memory Unification — T2 Migration Receipt (2026-07-04)

13 nodes migrated from `curated_graph.json` to
`~/.attune/memory/curated/*.md` (memory repo commit `7f55a40`).
State parity after hydrate cutover: **EXACT — 22/22 Redis keys
identical** (node hashes, edge lists, status set) vs the
pre-cutover snapshot. Eval gate (R5): class A ft 3/5·3/5, B 5/7,
C no crowding — matches the 2026-07-04 baseline.

| node_id | file | node_type |
|---|---|---|
| `project_context_20260701193125_070be411b98c` | `personalmemory_recall_is_file_backed_and_survives_process.md` | project_context |
| `reference_20260701193125_3c077c622099` | `canonical_recall_benchmark_numbers_and_methodology.md` | reference |
| `feedback_20260701193125_ffa455c1db15` | `prefer_real_round_trip_tests_over_mocks_when.md` | feedback |
| `user_context_20260701193125_9968105aa3dc` | `patrick_s_active_priority_make_attune_s_memory.md` | user_context |
| `user_context_20260702001507_facd3d69e6f6` | `goal_framing_attune_memory_is_the_product_harness.md` | user_context |
| `project_context_20260702001507_148bbbbb2a80` | `frictions_a_and_c_fixed_pr_1212_b.md` | project_context |
| `project_context_20260702004314_a6fb3022f1c6` | `memory_architecture_git_long_term_redis_short_term.md` | project_context |
| `user_context_20260702105705_3adbdf8d0ab2` | `two_layer_memory_protocol_ratified_curated_durable_only.md` | user_context |
| `feedback_20260702115027_05962918a6ef` | `patrick_reinforced_collaboration_patterns_caught_doing_good_2026.md` | feedback |
| `project_context_20260703013922_5da5d6cd7625` | `recall_loop_closed_the_digest_renders_live_from.md` | project_context |
| `project_context_20260703013922_37c45d962977` | `starter_reconciler_is_the_short_term_layer_s.md` | project_context |
| `feedback_20260704074647_741036a34853` | `query_first_recall_discipline.md` | feedback |
| `project_context_20260704075056_f8e3c2b19d62` | `redis_recall_decision_both_sequenced_2026_07_04.md` | project_context |

Edges: 9/9 carried as `edges_json` frontmatter on their source
node's file. `curated_graph.json` remains write-only legacy until
T4 (promote() writes files) lands.
