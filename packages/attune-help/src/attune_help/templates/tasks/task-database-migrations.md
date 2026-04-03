---
type: task
name: task-database-migrations
tags: [database, migrations, python, sql]
source: developer-guidance
---

# How to Create and Run Migrations Safely

## Set up Alembic in your project

Initialize Alembic to manage migrations alongside your
SQLAlchemy models:

```bash
pip install alembic sqlalchemy
cd your-project
alembic init migrations
```

Edit `migrations/env.py` to point at your models:

```python
# migrations/env.py
from myapp.models import Base

target_metadata = Base.metadata
```

Edit `alembic.ini` to use your database URL:

```ini
# alembic.ini
sqlalchemy.url = postgresql://localhost:5432/myapp
```

For production, override via environment variable in
`env.py`:

```python
from os import environ

config.set_main_option(
    "sqlalchemy.url",
    environ.get("DATABASE_URL", "sqlite:///local.db"),
)
```

## Create a migration

Auto-generate from model changes:

```bash
alembic revision --autogenerate -m "add users email column"
```

This compares your SQLAlchemy models to the current
database and generates the diff. Always review the
generated file -- autogenerate misses some changes
(data migrations, custom indexes, partial indexes).

## Write reversible migrations

Every migration should have both `upgrade()` and
`downgrade()`:

```python
"""Add email column to users table."""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f6e5d4c3b2a1"


def upgrade():
    op.add_column(
        "users",
        sa.Column("email", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_users_email", "users", ["email"], unique=True
    )


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
```

The `downgrade()` undoes `upgrade()` in reverse order.
If a migration is truly irreversible (dropping data),
raise an error in `downgrade()`:

```python
def downgrade():
    raise RuntimeError(
        "This migration is irreversible. "
        "Restore from backup to undo."
    )
```

## Handle data migrations separately

Never mix schema changes and data backfills in the same
migration. Create two:

**Migration 1 -- add the column:**

```python
def upgrade():
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(500), nullable=True),
    )
```

**Migration 2 -- backfill the data:**

```python
from alembic import op
from sqlalchemy import text


def upgrade():
    # Batch update to avoid locking the entire table
    conn = op.get_bind()
    while True:
        result = conn.execute(text(
            "UPDATE users "
            "SET full_name = first_name || ' ' || last_name "
            "WHERE full_name IS NULL "
            "LIMIT 1000"
        ))
        if result.rowcount == 0:
            break


def downgrade():
    op.execute(text(
        "UPDATE users SET full_name = NULL"
    ))
```

Batching prevents long-running transactions that lock
tables and block other queries.

## Test migrations before deploying

Run the full upgrade-downgrade cycle on a copy of your
production schema:

```bash
# Apply all migrations
alembic upgrade head

# Verify current state
alembic current

# Roll back the latest migration
alembic downgrade -1

# Re-apply to confirm idempotency
alembic upgrade head
```

For CI, add a migration test:

```python
def test_migrations_up_and_down(alembic_runner):
    """Verify all migrations apply and reverse cleanly."""
    alembic_runner.migrate_up_to("head")
    alembic_runner.migrate_down_to("base")
    alembic_runner.migrate_up_to("head")
```

## Run migrations in production

Apply with a pre-deploy step, not inside application
startup:

```bash
# In your deploy script, before starting the new code
alembic upgrade head
```

Never call `alembic upgrade head` from application
code at import time. If two instances start
simultaneously, they race to apply the same migration.

For Django projects, the equivalent workflow is:

```bash
python manage.py makemigrations
python manage.py migrate --plan  # review first
python manage.py migrate
```

## Checklist

- [ ] Each migration has a clear, descriptive message
- [ ] `upgrade()` and `downgrade()` are both implemented
- [ ] Schema and data changes are in separate migrations
- [ ] Data migrations use batched updates
- [ ] Migration tested with upgrade-downgrade-upgrade cycle
- [ ] Migration reviewed for table-locking operations
- [ ] Production deploy runs migration before new code

## Want to learn more?

- Say **"show me migration patterns"** for the full
  command reference, rollback strategies, and index
  management techniques
- Say **"what are database migrations?"** for the
  underlying concepts -- schema design, safety
  principles, and zero-downtime strategies
- Say **"I need to change my database schema"** for a
  5-minute quickstart
- Ask **"/release-prep"** to verify pending migrations
  are safe before deploying
- Ask **"/security-audit"** to check migration files
  for raw SQL injection risks
