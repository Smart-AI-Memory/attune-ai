---
type: reference
name: task-authentication-patterns
tags: [auth, security, python, patterns]
source: developer-guidance
---

# Reference: Authentication patterns

Complete catalog of authentication patterns for Python
APIs. Covers JWT, session management, OAuth2 flows,
password hashing, CSRF protection, rate limiting, and
common vulnerabilities.

## JWT patterns

### Token creation

```python
import os
from datetime import datetime, timedelta, timezone

import jwt

SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"


def create_token(
    user_id: str,
    role: str = "user",
    expires_minutes: int = 30,
) -> str:
    """Create a signed JWT with standard claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)
```

**Standard JWT claims:**

| Claim | Purpose | Required? |
|---|---|---|
| `sub` | Subject (user ID) | Yes |
| `exp` | Expiration time | Yes |
| `iat` | Issued at | Recommended |
| `iss` | Issuer identifier | For multi-service setups |
| `aud` | Audience (intended recipient) | For multi-service setups |
| `jti` | Unique token ID | For revocation lists |

### Token validation

```python
def decode_token(token: str) -> dict:
    """Decode and validate a JWT.

    Always specify algorithms explicitly to prevent
    algorithm confusion attacks.
    """
    return jwt.decode(
        token,
        SECRET,
        algorithms=[ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
```

**Validation checklist:**

| Check | What it prevents |
|---|---|
| Verify signature | Token forgery |
| Check `exp` | Replay attacks with expired tokens |
| Explicit `algorithms` list | Algorithm confusion (e.g., `none` algorithm) |
| Require expected claims | Missing-claim bypass |

### Refresh tokens

```python
REFRESH_EXPIRE_DAYS = 7


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def rotate_tokens(refresh_token: str) -> dict:
    """Exchange a refresh token for a new token pair.

    The old refresh token should be invalidated server-side
    after this call (token rotation).
    """
    payload = jwt.decode(
        refresh_token,
        SECRET,
        algorithms=[ALGORITHM],
    )
    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")

    user_id = payload["sub"]
    return {
        "access_token": create_token(user_id),
        "refresh_token": create_refresh_token(user_id),
    }
```

**When to use:** Pair short-lived access tokens (15-30 min)
with refresh tokens (7-30 days). Store refresh tokens
server-side so you can revoke them on logout or compromise.

## Session management

### Server-side sessions

```python
import secrets
from datetime import datetime, timedelta, timezone


def create_session(
    user_id: str,
    store: dict,
    max_age_hours: int = 24,
) -> str:
    """Create a server-side session and return its ID."""
    session_id = secrets.token_urlsafe(32)
    store[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)
        + timedelta(hours=max_age_hours),
    }
    return session_id
```

### Cookie security flags

| Flag | Purpose | Always set? |
|---|---|---|
| `HttpOnly` | Prevent JavaScript access (blocks XSS theft) | Yes |
| `Secure` | Send only over HTTPS | Yes in production |
| `SameSite=Lax` | Prevent CSRF on cross-origin requests | Yes |
| `SameSite=Strict` | Block all cross-origin cookie sending | For sensitive actions |
| `Max-Age` or `Expires` | Limit session lifetime | Yes |
| `Path=/` | Scope to the application root | Yes |

```python
response.set_cookie(
    key="session_id",
    value=session_id,
    httponly=True,
    secure=True,
    samesite="Lax",
    max_age=86400,  # 24 hours
)
```

## OAuth2 flows

### Authorization code flow (most common)

Use this for web applications where users sign in via a
third-party provider (Google, GitHub, etc.).

| Step | Who | Action |
|---|---|---|
| 1 | Client | Redirect user to provider's `/authorize` |
| 2 | User | Authenticates with the provider |
| 3 | Provider | Redirects back with an authorization code |
| 4 | Server | Exchanges code for access + refresh tokens |
| 5 | Server | Uses access token to call provider APIs |

**Key requirement:** The code-to-token exchange happens
server-side. The authorization code is single-use and
short-lived (typically 10 minutes).

### Client credentials flow

Use this for server-to-server communication where no user
is involved.

```python
import httpx


def get_service_token(
    client_id: str,
    client_secret: str,
    token_url: str,
) -> str:
    """Obtain a token using client credentials."""
    response = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "read:data",
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]
```

### OAuth2 flow comparison

| Flow | Use case | User involved? | Complexity |
|---|---|---|---|
| Authorization Code | Web apps, SPAs with backend | Yes | Medium |
| Authorization Code + PKCE | Mobile apps, SPAs without backend | Yes | Medium-high |
| Client Credentials | Server-to-server | No | Low |
| Device Code | CLI tools, smart TVs | Yes (on another device) | Medium |

## Password hashing

### bcrypt (recommended default)

```python
import bcrypt


def hash_password(password: str) -> str:
    """Hash with bcrypt. Rounds=12 is the minimum for
    production use."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8"),
    )
```

### argon2 (strongest, newer)

```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
)


def hash_password_argon2(password: str) -> str:
    """Hash with Argon2id (memory-hard, GPU-resistant)."""
    return ph.hash(password)


def verify_password_argon2(
    password: str, hashed: str
) -> bool:
    """Verify a password against its Argon2 hash."""
    try:
        return ph.verify(hashed, password)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: argon2 raises various exceptions
        # for invalid hashes. All mean "does not match."
        return False
```

### Hashing algorithm comparison

| Algorithm | GPU resistance | Memory cost | Adoption | Recommendation |
|---|---|---|---|---|
| **bcrypt** | Good | Low (4 KB) | Universal | Default choice for most apps |
| **argon2id** | Excellent | Configurable (64 MB+) | Growing | Best for high-security systems |
| **scrypt** | Good | Configurable | Moderate | Solid alternative |
| **PBKDF2** | Low | None | Legacy | Avoid for new projects |
| **MD5/SHA-1/SHA-256** | None | None | Outdated | Never use for passwords |

## CSRF protection

Cross-site request forgery targets session-based auth.
Token-based APIs using `Authorization` headers are
inherently protected because browsers do not attach
custom headers to cross-origin requests automatically.

**For session-based apps:**

```python
import secrets


def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(
    session_token: str, submitted_token: str
) -> bool:
    """Validate CSRF token using constant-time comparison."""
    return secrets.compare_digest(
        session_token, submitted_token
    )
```

**When CSRF protection is needed:**

| Auth method | CSRF risk? | Protection needed? |
|---|---|---|
| Session cookies | Yes | Yes -- use CSRF tokens or `SameSite=Strict` |
| JWT in `Authorization` header | No | No -- browsers do not auto-attach headers |
| JWT in cookies | Yes | Yes -- same risk as session cookies |

## Rate limiting auth endpoints

Authentication endpoints are brute-force targets. Rate
limiting slows down credential stuffing attacks.

```python
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional


class LoginRateLimiter:
    """Simple in-memory rate limiter for login attempts."""

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 300,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[datetime]] = (
            defaultdict(list)
        )

    def is_allowed(self, identifier: str) -> bool:
        """Check if a login attempt is allowed."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(
            seconds=self.window_seconds
        )
        # Remove expired entries
        self._attempts[identifier] = [
            t for t in self._attempts[identifier]
            if t > cutoff
        ]
        return (
            len(self._attempts[identifier])
            < self.max_attempts
        )

    def record_attempt(self, identifier: str) -> None:
        """Record a login attempt."""
        self._attempts[identifier].append(
            datetime.now(timezone.utc)
        )
```

**Rate limit recommendations:**

| Endpoint | Max attempts | Window | After limit |
|---|---|---|---|
| `/login` | 5 | 5 minutes | 429 Too Many Requests |
| `/register` | 3 | 10 minutes | 429 Too Many Requests |
| `/reset-password` | 3 | 15 minutes | 429 Too Many Requests |
| `/refresh` | 10 | 1 minute | 429 Too Many Requests |

## Common vulnerabilities

| Vulnerability | Risk | How it happens | Prevention |
|---|---|---|---|
| Token in URL query string | Token leaked in server logs, browser history, referrer headers | Passing `?token=abc` instead of `Authorization` header | Always use headers or `HttpOnly` cookies |
| No token expiration | Stolen token works forever | Missing `exp` claim in JWT | Always set `exp`; use short lifetimes (15-30 min) |
| Weak signing secret | Attacker can forge valid tokens | Short or guessable secret; committed to source control | Use 256+ bit random secret from env var |
| Plaintext passwords | Database breach exposes all credentials | Storing password directly instead of hash | Always hash with bcrypt or argon2 |
| Algorithm confusion | Attacker changes `alg` to `none` and bypasses signature | Not specifying `algorithms` list in `jwt.decode()` | Always pass explicit `algorithms=["HS256"]` |
| Missing rate limiting | Brute-force and credential stuffing attacks | No limit on login attempts | Rate limit all auth endpoints |
| Session fixation | Attacker forces a known session ID | Not regenerating session ID after login | Create a new session ID on authentication |
| CSRF on cookie auth | Attacker tricks user into making authenticated requests | Using cookies without `SameSite` or CSRF tokens | Set `SameSite=Lax` and use CSRF tokens |

## Want to learn more?

- "What are the trade-offs between these approaches?" --
  see the **concept** template for a high-level comparison
- "Walk me through adding JWT auth step by step" -- see
  the **task** template for a complete implementation guide
- Run `/security` to scan your code for authentication
  vulnerabilities like missing token validation or weak
  hashing
- Run `/code-quality` to review your middleware for
  exception handling and logging patterns

## Related Topics

- **Concept**: Authentication patterns -- when to use
  sessions vs JWT vs OAuth2, and the principle of never
  rolling your own crypto
- **Task**: Authentication patterns -- step-by-step guide
  for adding JWT authentication to a FastAPI or Flask API
- **Quickstart**: Authentication patterns -- 5-step minimal
  guide for adding authentication to an API
