---
type: concept
name: task-authentication-patterns
tags: [auth, security, python, patterns]
source: developer-guidance
---

# Concept: Authentication patterns

## What

Authentication is the process of verifying that a user or
service is who they claim to be. An authentication pattern
is the mechanism you choose to carry proof of identity
between requests: a session cookie, a signed token, a
delegated grant, or a long-lived credential. Each pattern
trades off simplicity, security, scalability, and user
experience differently.

## Why

A weak authentication layer is the front door to every
other vulnerability. If an attacker can forge a token, hijack
a session, or guess a password, access controls downstream
are irrelevant. Choosing the right pattern for your use case
prevents entire categories of attacks before they start.
Rolling your own crypto or inventing a custom token format
is the most expensive mistake you can make -- the cost is
not writing the code, it is discovering the flaw in
production.

## Approach comparison

| Approach | Security level | Complexity | Session management | Best for |
|---|---|---|---|---|
| **Session-based** | High (server-side state) | Low | Server stores session in memory/DB; cookie holds session ID | Traditional web apps, server-rendered pages, apps where you control both client and server |
| **JWT (JSON Web Tokens)** | Medium-high (depends on implementation) | Medium | Stateless; token carries claims; server validates signature | APIs, SPAs, microservices, mobile apps needing stateless auth |
| **OAuth2** | High (delegated authority) | High | Delegated to identity provider; tokens are scoped and time-limited | Third-party integrations, "Sign in with Google/GitHub", B2B APIs |
| **Long-lived credentials** | Low-medium (shared secret risk) | Low | No session; credential sent with every request | Server-to-server communication, CI pipelines, internal tooling |

## Key principles

- **Never roll your own crypto.** Use established libraries
  like `PyJWT`, `passlib`, `authlib`, or `python-jose`.
  Custom token signing, password hashing, or encryption
  is where security bugs hide.
- **Hash passwords, never encrypt them.** Hashing is
  one-way. If your database leaks, attackers cannot reverse
  a bcrypt hash. If you encrypted passwords, the encryption
  key becomes a single point of failure.
- **Tokens expire.** Every token should have an expiration
  time. Short-lived access tokens (15-60 minutes) plus
  longer-lived refresh tokens limit the blast radius of a
  stolen credential.
- **Transport security is non-negotiable.** Tokens and
  session cookies must travel over HTTPS. A token sent
  over plain HTTP can be intercepted by anyone on the
  network.
- **Least privilege by default.** Tokens should carry only
  the claims needed for the operation. A token that grants
  admin access to every endpoint is a liability.

## The cost of getting it wrong

```python
# This stores passwords in plaintext -- a data breach
# exposes every user's credentials immediately
def register(username: str, password: str) -> None:
    db.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password),
    )
```

When the database is compromised -- and breaches happen --
every user's password is readable. Credential stuffing
attacks follow within hours because users reuse passwords
across services. A proper bcrypt hash makes the stolen data
useless.

## Want to learn more?

- "How do I add JWT auth to my API?" -- see the **task**
  template for a step-by-step guide with FastAPI and Flask
- "Show me all the patterns with code examples" -- see
  the **reference** template for JWT, OAuth2, session, and
  password hashing patterns
- "I just need auth working in 10 minutes" -- see the
  **quickstart** template for a 5-step guide
- Run `/security` to scan your code for authentication
  vulnerabilities like hardcoded secrets or missing token
  validation
- Run `/code-quality` to check your middleware patterns
  for common issues

## Related Topics

- **Task**: Authentication patterns -- step-by-step guide
  for adding JWT authentication to an API
- **Reference**: Authentication patterns -- full pattern
  catalog covering JWT, OAuth2, sessions, password hashing,
  CSRF protection, and common vulnerabilities
- **Quickstart**: Authentication patterns -- 5-step minimal
  guide for adding authentication to an API
