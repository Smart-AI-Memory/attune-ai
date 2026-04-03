---
type: concept
name: task-api-endpoint-design
tags: [api, python, rest, patterns]
source: developer-guidance
---

# Concept: API endpoint design

## What

API endpoint design is the practice of defining how your
application exposes functionality over HTTP. It covers URL
structure, request validation, error responses, status
codes, and versioning. A well-designed API is predictable
-- clients can guess how an unfamiliar endpoint works
because it follows the same conventions as every other
endpoint.

## Why

Bad API design compounds. Every inconsistency becomes a
FAQ in your docs, a special case in your client SDK, and
a source of bugs for every consumer. If `/users` returns
a list but `/projects` returns a wrapper object, every
client must handle both shapes. If `POST /items` returns
`200` but `POST /orders` returns `201`, error handling
diverges. The cost of fixing these inconsistencies after
clients depend on them is enormous. The cost of getting
them right upfront is a few minutes of thought per
endpoint.

## REST conventions

REST is not a protocol -- it is a set of conventions
built on HTTP. The core idea is that URLs identify
resources (nouns), and HTTP methods define operations
(verbs).

| Method | Purpose | Idempotent? | Request body? | Common status codes |
|---|---|---|---|---|
| `GET` | Retrieve a resource or collection | Yes | No | `200 OK`, `404 Not Found` |
| `POST` | Create a new resource | No | Yes | `201 Created`, `400 Bad Request`, `422 Unprocessable Entity` |
| `PUT` | Replace a resource entirely | Yes | Yes | `200 OK`, `404 Not Found` |
| `PATCH` | Partially update a resource | No | Yes | `200 OK`, `404 Not Found`, `422 Unprocessable Entity` |
| `DELETE` | Remove a resource | Yes | No | `204 No Content`, `404 Not Found` |

**Idempotent** means calling it twice with the same input
produces the same result. `GET`, `PUT`, and `DELETE` are
idempotent by convention. `POST` and `PATCH` are not.

## Request validation

Every endpoint should validate its input before doing any
work. Validation happens in two layers:

1. **Schema validation** -- Is the request body the right
   shape? Are required fields present? Are types correct?
   This is where Pydantic or marshmallow shines.
2. **Business validation** -- Is the value semantically
   valid? Does the referenced user exist? Is the quantity
   positive? This happens in your application logic.

Schema failures return `422 Unprocessable Entity`.
Business failures return `400 Bad Request` or a more
specific code like `409 Conflict`.

## Error response format

Consistent error responses save hours of debugging for
API consumers. Pick one format and use it everywhere.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body validation failed",
    "details": [
      {
        "field": "email",
        "message": "Not a valid email address"
      }
    ]
  }
}
```

The `code` field is machine-readable (clients can switch
on it). The `message` field is human-readable. The
`details` array provides per-field granularity for
validation errors.

## Versioning

APIs change. Versioning lets you evolve without breaking
existing clients.

| Strategy | Example | Pros | Cons |
|---|---|---|---|
| URL path | `/v1/users` | Obvious, easy to route | Pollutes URL namespace |
| Header | `Accept: application/vnd.api+json;version=2` | Clean URLs | Harder to test in browser |
| Query param | `/users?version=2` | Easy to add | Easy to forget |

URL path versioning is the most common and the easiest
to reason about. Use it unless you have a strong reason
not to.

## REST vs GraphQL

| Consideration | REST | GraphQL |
|---|---|---|
| Best for | CRUD operations, simple resource models | Complex nested queries, mobile clients needing minimal payloads |
| Caching | Built-in HTTP caching by URL | Requires custom caching (no URL-based cache key) |
| Learning curve | Low -- HTTP methods are well-understood | Higher -- schema, resolvers, query language |
| Over-fetching | Common (returns full objects) | Solved (client specifies exact fields) |
| Under-fetching | Common (requires multiple requests) | Solved (single query, nested data) |
| Tooling | Mature (Swagger, Postman, curl) | Growing (GraphiQL, Apollo DevTools) |

**Rule of thumb:** Start with REST. Move specific
endpoints to GraphQL when clients consistently need
deeply nested or highly selective queries.

## Want to learn more?

- "How do I build an endpoint from scratch?" -- see the
  **task** template for a step-by-step implementation
  guide
- "Show me all the status codes and patterns" -- see the
  **reference** template for the complete catalog
- Run `/security` to audit your endpoints for input
  validation gaps and injection risks
- Run `/code-quality` to check handler functions for
  consistency and error handling patterns

## Related Topics

- **Task**: API endpoint design -- step-by-step guide
  from route definition to tested endpoint
- **Reference**: API endpoint design -- full catalog of
  status codes, validation patterns, and configuration
- **Quickstart**: API endpoint design -- 5-step guide to
  add a new endpoint
