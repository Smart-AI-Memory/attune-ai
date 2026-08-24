# Lanternfish — Operations Notes (Q2)

## Incident 2417 — staging backlog

A four-hour ingest backlog traced to contention on the heliotrope
advisory lock: a long-running compaction job held the lock past its
lease, so the QuorumLattice scheduler could not start new fan-out
cycles. Workers were healthy and idle the whole time — the backlog
was purely a scheduling stall.

Mitigation applied: compaction moved to its own lease with a hard
timeout; scheduler alerts now page when a fan-out cycle is delayed
more than five minutes.

## Routine load

Typical weekday load is 40–60 bundles per hour with fan-out cycles
completing in under 90 seconds. Weekend load drops by roughly half.
