---
type: reference
subtype: tabular
name: task-database-migrations
tags: [database, migrations, python, sql]
source: developer-guidance
---

# Database Migrations Reference

Complete reference for migration commands, rollback
patterns, zero-downtime techniques, and common pitfalls
across Alembic and Django.

## Alembic commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `alembic init migrations` | Create migration directory and config | Project setup (once) |
| `alembic revision -m "msg"` | Create empty migration file | Manual migrations (data, custom DDL) |
| `alembic revision --autogenerate -m "msg"` | Generate migration from model diff | After changing SQLAlchemy models |
| `alembic upgrade head` | Apply all pending migrations | Deploy, CI, local dev |
| `alembic upgrade +1` | Apply next single migration | Step-by-step debugging |
| `alembic downgrade -1` | Roll back the last migration | Fixing a bad migration |
| `alembic downgrade base` | Roll back all migrations | Full reset (dev only) |
| `alembic current` | Show current migration revision | Verify state |
| `alembic history` | List all migrations in order | Review migration chain |
| `alembic heads` | Show latest revision(s) | Detect branch conflicts |
| `alembic merge -m "merge"` | Merge diverged migration branches | After parallel development |
| `alembic stamp head` | Mark DB as current without running | Bootstrapping existing databases |
| `alembic check` | Verify models match DB (no pending) | CI gate |

## Django migration commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `python manage.py makemigrations` | Generate migrations from model changes | After changing models |
| `python manage.py migrate` | Apply all pending migrations | Deploy, CI, local dev |
| `python manage.py migrate app_name 0003` | Migrate to a specific migration | Rollback to a known state |
| `python manage.py migrate app_name zero` | Roll back all migrations for an app | Full reset of one app |
| `python manage.py showmigrations` | List all migrations and their status | Verify state |
| `python manage.py sqlmigrate app_name 0004` | Show SQL for a migration (dry run) | Review before applying |
| `python manage.py migrate --plan` | Show what would be applied | Pre-deploy review |
| `python manage.py squashmigrations app 0001 0010` | Combine migrations into one | Reduce migration count |

## Rollback patterns

| Scenario | Rollback strategy | Risk | Notes |
|----------|------------------|------|-------|
| **Added a column** | `op.drop_column()` in downgrade | Low | Safe if column is nullable and unused |
| **Added a table** | `op.drop_table()` in downgrade | Low | Safe if no data or foreign keys |
| **Dropped a column** | Cannot auto-recover | High | Restore from backup; data is gone |
| **Renamed a column** | Rename back in downgrade | Medium | Update application code in both directions |
| **Added NOT NULL** | Drop constraint in downgrade | Medium | Existing NULLs must be handled first |
| **Added foreign key** | Drop constraint in downgrade | Low | Application code must handle orphans |
| **Data backfill** | Reverse transformation or NULL out | Medium | May lose derived data |
| **Changed column type** | Cast back in downgrade | High | Data truncation or precision loss possible |

## Zero-downtime techniques

### Expand-contract (recommended)

The safest pattern for any non-trivial schema change.
Three separate deploys, each independently safe:

**Step 1 -- Expand:**

```python
def upgrade():
    # Add new column, nullable, with default
    op.add_column(
        "users",
        sa.Column("email_v2", sa.String(320), nullable=True),
    )
```

Deploy code that writes to both `email` and `email_v2`.

**Step 2 -- Migrate data:**

```python
def upgrade():
    conn = op.get_bind()
    conn.execute(text(
        "UPDATE users SET email_v2 = email "
        "WHERE email_v2 IS NULL"
    ))
```

**Step 3 -- Contract:**

```python
def upgrade():
    op.drop_column("users", "email")
    op.alter_column(
        "users", "email_v2",
        new_column_name="email",
        nullable=False,
    )
```

Deploy code that only uses `email`.

### Adding an index without downtime

PostgreSQL:

```python
def upgrade():
    # CONCURRENTLY avoids locking the table
    op.execute(text(
        "CREATE INDEX CONCURRENTLY ix_users_email "
        "ON users (email)"
    ))
```

MySQL (5.6+):

```python
def upgrade():
    # InnoDB supports online DDL for indexes
    op.create_index("ix_users_email", "users", ["email"])
```

SQLite:

```python
def upgrade():
    # SQLite indexes are always non-blocking
    op.create_index("ix_users_email", "users", ["email"])
```

### Adding a NOT NULL constraint safely

```python
# Step 1: Add column as nullable
def upgrade():
    op.add_column(
        "orders",
        sa.Column("status", sa.String(20), nullable=True),
    )

# Step 2: Backfill existing rows
def upgrade():
    op.execute(text(
        "UPDATE orders SET status = 'pending' "
        "WHERE status IS NULL"
    ))

# Step 3: Add the constraint
def upgrade():
    op.alter_column(
        "orders", "status", nullable=False,
        server_default="pending",
    )
```

## Foreign key strategies

| Strategy | Pros | Cons | When to use |
|----------|------|------|-------------|
| **Add FK with NOT VALID (Postgres)** | No full table scan on creation | Must `VALIDATE` later | Large tables in production |
| **Add FK normally** | Simple, fully validated | Locks table during creation | Small tables or maintenance windows |
| **Application-level FK** | No DB constraint | Orphans possible, no cascade | Cross-database references |
| **Deferred FK** | Checked at commit, not insert | Slightly slower commits | Circular references, bulk inserts |

PostgreSQL NOT VALID example:

```python
def upgrade():
    # Add constraint without validating existing rows
    op.execute(text(
        "ALTER TABLE orders "
        "ADD CONSTRAINT fk_orders_user "
        "FOREIGN KEY (user_id) REFERENCES users(id) "
        "NOT VALID"
    ))

# Separate migration: validate in background
def upgrade():
    op.execute(text(
        "ALTER TABLE orders "
        "VALIDATE CONSTRAINT fk_orders_user"
    ))
```

## Index management

| Index type | Use case | Create syntax |
|-----------|----------|---------------|
| **B-tree (default)** | Equality and range queries | `op.create_index("ix_name", "table", ["col"])` |
| **Unique** | Enforce uniqueness | `op.create_index("ix_name", "table", ["col"], unique=True)` |
| **Partial** | Index a subset of rows | `CREATE INDEX ix_name ON table (col) WHERE active = true` |
| **Composite** | Multi-column queries | `op.create_index("ix_name", "table", ["col1", "col2"])` |
| **GIN** | Full-text search, JSONB | `CREATE INDEX ix_name ON table USING gin (data)` |
| **Expression** | Computed values | `CREATE INDEX ix_name ON table (lower(email))` |

**Column order in composite indexes matters.** Put the
most selective column first (the one that filters out
the most rows). Queries can use a composite index for
prefix columns only -- `(a, b, c)` supports queries on
`a`, `(a, b)`, and `(a, b, c)`, but not `b` alone.

## Common pitfalls

| Pitfall | What happens | Prevention |
|---------|-------------|------------|
| **Editing applied migrations** | Checksum mismatch; Alembic refuses to run | Migrations are append-only; create a new one |
| **Large table ALTER without CONCURRENTLY** | Table locked for minutes/hours; app unresponsive | Use `CREATE INDEX CONCURRENTLY`, batch data updates |
| **NOT NULL on existing column without default** | Fails if any rows have NULL | Backfill NULLs first, then add constraint |
| **Dropping a column that code still reads** | `ProgrammingError` at runtime | Use expand-contract; remove code first |
| **Running migration inside app startup** | Race condition with multiple instances | Run migrations in deploy pipeline, not app code |
| **Missing downgrade function** | Cannot roll back a bad deploy | Always write `downgrade()` or raise explicitly |
| **Autogenerate missing custom DDL** | Partial indexes, triggers, functions not detected | Review every autogenerated migration |
| **Data migration in same file as schema** | Cannot roll back schema without losing data logic | One concern per migration file |
| **Long-running transaction** | Holds locks, blocks other queries, risks timeout | Batch updates with `LIMIT`, commit between batches |
| **Testing only on empty DB** | Migration works on dev, locks production for hours | Test on a production-sized dataset copy |

## Data migration patterns

### Batch update (recommended)

```python
def upgrade():
    conn = op.get_bind()
    batch_size = 1000
    while True:
        result = conn.execute(text(
            f"UPDATE users "
            f"SET normalized_email = lower(email) "
            f"WHERE normalized_email IS NULL "
            f"LIMIT {batch_size}"
        ))
        if result.rowcount == 0:
            break
```

### Backfill with progress logging

```python
def upgrade():
    conn = op.get_bind()
    total = conn.execute(text(
        "SELECT count(*) FROM users WHERE status IS NULL"
    )).scalar()
    processed = 0
    batch_size = 5000

    while processed < total:
        conn.execute(text(
            "UPDATE users SET status = 'active' "
            "WHERE status IS NULL LIMIT :batch"
        ), {"batch": batch_size})
        processed += batch_size
        print(f"  Backfilled {min(processed, total)}/{total}")
```

### Copy-and-swap for column type changes

```python
# Step 1: Add new column with new type
def upgrade():
    op.add_column("events", sa.Column(
        "timestamp_v2", sa.DateTime(timezone=True),
    ))

# Step 2: Backfill with type conversion
def upgrade():
    op.execute(text(
        "UPDATE events SET timestamp_v2 = "
        "timestamp AT TIME ZONE 'UTC'"
    ))

# Step 3: Swap columns
def upgrade():
    op.drop_column("events", "timestamp")
    op.alter_column(
        "events", "timestamp_v2",
        new_column_name="timestamp",
    )
```

## Want to learn more?

- Say **"what are database migrations?"** for the
  concepts -- schema design, safety principles, and
  zero-downtime strategies
- Say **"how do I create a migration?"** for the
  step-by-step guide with Alembic and Django
- Say **"I need to change my database schema"** for a
  5-minute quickstart
- Ask **"/release-prep"** to verify all pending
  migrations are reviewed before deploying
- Ask **"/security-audit"** to check migration files
  for raw SQL injection or unsafe string interpolation
