---
type: quickstart
name: task-authentication-patterns
tags: [auth, security, python, patterns]
source: developer-guidance
---

# Quickstart: Add authentication to your API

Five steps to go from no authentication to a working
JWT-protected API.

## 1. Install dependencies

```bash
pip install PyJWT bcrypt
```

Set your signing secret as an environment variable:

```bash
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

Never hardcode the secret in your source code.

## 2. Hash passwords on registration

```python
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")
```

Store the hash in your database. Never store the
original password.

## 3. Create and validate tokens

```python
import os
from datetime import datetime, timedelta, timezone

import jwt

SECRET = os.environ["JWT_SECRET"]


def create_token(user_id: str) -> str:
    """Create a JWT that expires in 30 minutes."""
    return jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=30),
        },
        SECRET,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict:
    """Validate and decode a JWT."""
    return jwt.decode(
        token, SECRET, algorithms=["HS256"]
    )
```

## 4. Protect your routes

Extract the token from the `Authorization: Bearer <token>`
header and validate it before processing the request.

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()


async def get_current_user(
    creds=Depends(security),
) -> dict:
    """Middleware that validates the bearer token."""
    try:
        return decode_token(creds.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401)


@app.get("/profile")
async def profile(user=Depends(get_current_user)):
    return {"user_id": user["sub"]}
```

## 5. Add a login endpoint

```python
@app.post("/login")
async def login(username: str, password: str):
    user = get_user_by_username(username)
    if not user or not bcrypt.checkpw(
        password.encode("utf-8"),
        user.hashed_password.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )
    return {
        "access_token": create_token(str(user.id)),
        "token_type": "bearer",
    }
```

Return the same error for wrong username and wrong
password to prevent username enumeration.

## Verify

Run `/security` on your auth module to check for
hardcoded secrets, missing token expiration, and
plaintext password storage.

## Want to learn more?

- "Walk me through the full process with refresh tokens"
  -- see the **task** template for a complete guide
- "Show me OAuth2, CSRF, and rate limiting patterns" --
  see the **reference** template for the full catalog
- "What are the trade-offs between JWT and sessions?" --
  see the **concept** template for a comparison of all
  approaches

## Related Topics

- **Concept**: Authentication patterns -- when to use
  sessions vs JWT vs OAuth2, and the principle of never
  rolling your own crypto
- **Task**: Authentication patterns -- step-by-step guide
  covering password hashing, middleware, refresh tokens,
  and protected routes
- **Reference**: Authentication patterns -- all patterns
  with code examples, vulnerability table, and rate
  limiting guidance
