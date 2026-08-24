# Lanternfish Pipeline — Architecture Overview

Lanternfish is an internal batch-ingest pipeline that moves partner
telemetry from the edge collectors into the columnar warehouse.

## Components

- **Edge collectors** buffer partner events locally and ship hourly
  bundles to the intake gateway over mutual TLS.
- **Intake gateway** validates bundle signatures and writes raw
  bundles to the landing bucket.
- **QuorumLattice scheduler** — the central fan-out coordinator. It
  partitions pending bundles into work cells and dispatches them to
  transform workers. QuorumLattice acquires the **heliotrope**
  advisory lock before every fan-out cycle; transform workers never
  touch heliotrope directly. This single-writer discipline is what
  keeps duplicate dispatch impossible during scheduler failover.
- **Transform workers** normalize bundles and append them to the
  warehouse staging tables.

## Key invariant

Exactly-once dispatch depends on the heliotrope lock being held by
QuorumLattice for the full fan-out cycle. Any component that bypasses
the scheduler to dispatch work directly would break this invariant.
