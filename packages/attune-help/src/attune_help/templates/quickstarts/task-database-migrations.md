---
type: quickstart
name: task-database-migrations
tags: [database, migrations, python, sql]
source: developer-guidance
---

# Quickstart: Change Your Database Schema

Add a column to an existing table safely in 5 steps
using Alembic and SQLAlchemy.

## Step 1: Install Alembic

```bash
pip install alembic sqlalchemy
alembic init migrations
```

Edit `migrations/env.py` to import your models:

```python
# migrations/env.py
from myapp.models import Base

target_metadata = Base.metadata
```

## Step 2: Update your model

Add the new column to your SQLAlchemy model:

```python
# src/myapp/models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)  # new
```

## Step 3: Generate the migration

```bash
alembic revision --autogenerate -m "add email to users"
```

Open the generated file and verify it looks right:

```python
def upgrade():
    op.add_column(
        "users",
        sa.Column("email", sa.String(255), nullable=True),
    )


def downgrade():
    op.drop_column("users", "email")
```

Always make new columns `nullable=True` first. You can
add a NOT NULL constraint in a later migration after
backfilling existing rows.

## Step 4: Test the migration

```bash
# Apply it
alembic upgrade head

# Verify it applied
alembic current

# Roll it back
alembic downgrade -1

# Re-apply to confirm it's repeatable
alembic upgrade head
```

If any step fails, fix the migration file before it
reaches staging or production.

## Step 5: Deploy

Run the migration in your deploy pipeline, before
starting the new application code:

```bash
# In your deploy script
alembic upgrade head
# Then start the app
```

Never run migrations inside application startup code.
If two instances start at the same time, they race to
apply the same migration.

**Done.** Your schema change is versioned, reversible,
and deployed safely.

## What you get

| Feature | How it works |
|---------|-------------|
| Version control | Each migration has a unique ID and message |
| Reversibility | `downgrade()` undoes the change cleanly |
| Auto-generation | Alembic diffs your models against the DB |
| Environment safety | Same migration runs in dev, staging, prod |

## Want to learn more?

- Say **"how do I create a migration?"** for the full
  guide -- data migrations, batch updates, and testing
  strategies
- Say **"show me migration patterns"** for the command
  reference, rollback patterns, and zero-downtime
  techniques
- Say **"what are database migrations?"** for schema
  design principles, safety rules, and the
  expand-contract pattern
- Ask **"/release-prep"** to check for pending
  migrations before your next deploy
- Ask **"/security-audit"** to scan migration files for
  SQL injection risks
