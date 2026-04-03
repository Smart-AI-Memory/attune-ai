---
type: concept
name: task-database-migrations
tags: [database, migrations, python, sql]
source: developer-guidance
---

# Database Migrations

A database migration is a versioned, repeatable change to
your database schema. Migrations let you evolve your
schema alongside your application code -- adding columns,
creating tables, changing constraints -- while keeping
every environment (dev, staging, production) in sync.
Without migrations, schema changes are ad-hoc SQL scripts
that drift between environments and break deployments.

## Schema vs data migrations

These are fundamentally different operations with
different risk profiles:

| Type | What changes | Risk level | Rollback difficulty | Downtime? | Example |
|------|-------------|------------|---------------------|-----------|---------|
| **Schema (additive)** | New tables, columns, indexes | Low | Drop the new object | Usually no | `ALTER TABLE users ADD COLUMN email VARCHAR(255)` |
| **Schema (destructive)** | Drop columns, rename tables | High | Requires backup restore | Often yes | `ALTER TABLE users DROP COLUMN legacy_name` |
| **Schema (constraint)** | Add NOT NULL, foreign keys, unique | Medium | Drop the constraint | Depends on table size | `ALTER TABLE orders ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)` |
| **Data** | Backfill values, transform rows | High | Reverse transformation needed | Usually no (but slow) | `UPDATE users SET full_name = first_name \|\| ' ' \|\| last_name` |
| **Index** | Create or drop indexes | Medium | Drop or recreate | No (if concurrent) | `CREATE INDEX CONCURRENTLY idx_users_email ON users(email)` |

The key insight: additive schema changes are almost
always safe. Destructive changes and data migrations are
where things go wrong.

## Migration safety principles

1. **One migration, one concern.** A migration that adds
   a column AND backfills data is harder to debug and
   harder to roll back. Split them.
2. **Always write a reverse.** If your migration tool
   supports `downgrade()`, write it. If the migration is
   truly irreversible, document why.
3. **Test on a copy of production data.** A migration
   that works on an empty dev database can lock a
   production table with 50 million rows for minutes.
4. **Never assume the migration runs alone.** In a
   running application, reads and writes happen during
   the migration. Design for concurrent access.
5. **Migrations are append-only.** Never edit a migration
   that has already been applied to any environment.
   Create a new one instead.

## Data integrity during migrations

The most dangerous moment for data integrity is between
deploying new code and completing the migration. If your
new code expects a column that doesn't exist yet, or
the migration removes a column that old code still
reads, you get runtime errors.

The expand-contract pattern solves this:

1. **Expand** -- Add the new column (nullable, with a
   default). Deploy code that writes to both old and new.
2. **Migrate** -- Backfill existing rows. Both old and
   new code still work.
3. **Contract** -- Remove the old column. Deploy code
   that only uses the new one.

Each step is a separate migration and a separate deploy.
No single step breaks running code.

## Zero-downtime strategies

Zero-downtime migrations require that the database
schema is compatible with both the old and new
application code at every step:

| Strategy | How it works | Tradeoff |
|----------|-------------|----------|
| **Expand-contract** | Add new, backfill, remove old across 3 deploys | More deploys, but each is safe |
| **Dual-write** | Write to both old and new columns during transition | Application complexity during migration window |
| **Feature flags** | Toggle code paths without schema coupling | Requires feature flag infrastructure |
| **Blue-green deploys** | Run old and new app versions side by side | Requires schema compatibility with both versions |

## What makes migrations go wrong

Most migration failures come from the same few mistakes:
running untested migrations on large tables, editing
migrations that were already applied, mixing schema and
data changes in one migration, or forgetting that
production has concurrent traffic. A disciplined workflow
-- test locally, review the SQL, run on staging first --
eliminates all four.

## Want to learn more?

- Say **"how do I create a migration?"** for a
  step-by-step guide with Alembic and Django
- Say **"show me migration patterns"** for the full
  command reference, rollback strategies, and pitfall
  table
- Say **"I need to change my database schema"** for a
  5-minute quickstart
- Ask **"/release-prep"** to run pre-deploy checks
  including pending migration review
- Ask **"/security-audit"** to scan migration files for
  SQL injection risks or unsafe raw SQL
