---
type: task
name: task-authentication-patterns
tags: [auth, security, python, patterns]
source: developer-guidance
---

# Task: Add JWT authentication to an API

Add token-based authentication to a Python API using JWT.
This guide walks you through password hashing, token
creation, middleware setup, and protecting routes.

## Prerequisites

- A Python API framework (FastAPI or Flask)
- `pip install PyJWT bcrypt` (or `passlib[bcrypt]`)
- Basic understanding of HTTP headers and middleware

## Steps

### 1. Set up password hashing

Never store passwords in plaintext. Use bcrypt, which
is slow by design -- that slowness is what makes brute-
force attacks impractical.

```python
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(
        password.encode("utf-8"), salt
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8"),
    )
```

Use `rounds=12` or higher. Lower values hash faster but
are easier to brute-force.

### 2. Create token utilities

Build functions to create and validate JWTs. Keep the
signing secret out of your source code -- load it from
an environment variable.

```python
import os
from datetime import datetime, timedelta, timezone

import jwt


SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(
    user_id: str,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is malformed or
            signature is invalid.
    """
    return jwt.decode(
        token, SECRET, algorithms=[ALGORITHM]
    )
```

**Important:** The `algorithms` parameter in `decode` must
be a list and must match what you used in `encode`. Omitting
it allows algorithm confusion attacks.

### 3. Build the authentication middleware

The middleware extracts the token from the `Authorization`
header, validates it, and attaches the user identity to the
request context.

**FastAPI:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
) -> dict:
    """Validate the bearer token and return user claims."""
    try:
        payload = decode_token(credentials.credentials)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
```

**Flask:**

```python
from functools import wraps

from flask import g, jsonify, request


def require_auth(f):
    """Decorator to require a valid JWT on a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith(
            "Bearer "
        ):
            return jsonify({"error": "Missing token"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            g.user = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated
```

### 4. Protect your routes

Apply the middleware to routes that require authentication.

**FastAPI:**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/profile")
async def get_profile(
    user: dict = Depends(get_current_user),
):
    """Return the authenticated user's profile."""
    return {"user_id": user["sub"]}


@app.get("/health")
async def health():
    """Public endpoint -- no auth required."""
    return {"status": "ok"}
```

**Flask:**

```python
@app.route("/profile")
@require_auth
def get_profile():
    """Return the authenticated user's profile."""
    return jsonify({"user_id": g.user["sub"]})


@app.route("/health")
def health():
    """Public endpoint -- no auth required."""
    return jsonify({"status": "ok"})
```

### 5. Add a login endpoint

The login endpoint verifies credentials and returns a
token. This is the only endpoint that handles passwords.

```python
@app.post("/login")
async def login(username: str, password: str):
    """Authenticate and return an access token."""
    user = get_user_by_username(username)
    if not user or not verify_password(
        password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(user_id=str(user.id))
    return {"access_token": token, "token_type": "bearer"}
```

**Never leak whether the username or the password was
wrong.** Always return the same generic error message for
both cases to prevent username enumeration.

### 6. Add refresh token support (optional)

Short-lived access tokens (15-30 min) paired with longer-
lived refresh tokens (7-30 days) reduce the impact of a
stolen token while keeping users logged in.

```python
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        ),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)
```

Store refresh tokens server-side (database or Redis) so
you can revoke them if a user logs out or a token is
compromised.

### 7. Review with tooling

Run `/security` on your auth module to detect:

- Hardcoded secrets or weak signing algorithms
- Missing token expiration
- Plaintext password storage

Run `/code-quality` to check middleware patterns for
exception handling issues or missing logging.

## Verification

After adding authentication:

- [ ] Passwords are hashed with bcrypt (or argon2), never
      stored in plaintext
- [ ] Tokens have an expiration time (`exp` claim)
- [ ] The `algorithms` parameter is explicitly set in
      `jwt.decode()`
- [ ] The signing secret comes from an environment variable,
      not source code
- [ ] Protected routes return 401 for missing or invalid
      tokens
- [ ] Login returns the same error for bad username and bad
      password (no enumeration)
- [ ] HTTPS is required in production

## Want to learn more?

- "What are the trade-offs between session auth and JWT?"
  -- see the **concept** template for a comparison of all
  approaches
- "Show me refresh tokens, OAuth2, and CSRF patterns" --
  see the **reference** template for the full catalog
- "I just need auth working right now" -- see the
  **quickstart** template for a minimal 5-step guide

## Related Topics

- **Concept**: Authentication patterns -- when to use
  sessions vs JWT vs OAuth2, and the principle of never
  rolling your own crypto
- **Reference**: Authentication patterns -- full pattern
  catalog covering JWT, OAuth2, sessions, password hashing,
  and common vulnerabilities
- **Quickstart**: Authentication patterns -- 5-step minimal
  guide for adding authentication to an API
