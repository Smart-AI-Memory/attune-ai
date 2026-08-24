# Lanternfish — Roadmap

## Near term

- Per-partner ingest quotas at the intake gateway.
- Structured rejection reports for signature failures.

## Next quarter: shard the scheduler

The QuorumLattice scheduler is the last global singleton in the
pipeline. The plan is to shard it into per-tenant cells, each with
its own advisory lock, retiring the single global heliotrope lock.
Incident 2417 showed that one slow lock holder can stall every
tenant at once; per-tenant cells contain that blast radius.

Open question: whether cross-tenant deduplication still needs a
narrow global critical section after sharding, or whether bundle
signatures make it unnecessary.
