---
type: reference
name: task-api-endpoint-design
tags: [api, python, rest, patterns]
source: developer-guidance
---

# Reference: API endpoint patterns

Complete catalog of HTTP status codes, validation
patterns, pagination strategies, rate limiting, CORS,
OpenAPI generation, error formats, and versioning for
Python API development.

## HTTP status codes

### Success codes

| Code | Name | When to use | Example |
|---|---|---|---|
| `200` | OK | Request succeeded, response has a body | `GET /items/123` returns the item |
| `201` | Created | A new resource was created | `POST /items` returns the new item |
| `204` | No Content | Success but no response body | `DELETE /items/123` returns nothing |

### Client error codes

| Code | Name | When to use | Example |
|---|---|---|---|
| `400` | Bad Request | Business logic validation failed | Quantity exceeds stock |
| `401` | Unauthorized | No valid credentials provided | Missing or expired token |
| `403` | Forbidden | Authenticated but not authorized | User lacks admin role |
| `404` | Not Found | Resource does not exist | `GET /items/unknown-id` |
| `405` | Method Not Allowed | Wrong HTTP method for this route | `DELETE /items` (collection) |
| `409` | Conflict | Request conflicts with current state | Duplicate name, version conflict |
| `422` | Unprocessable Entity | Schema validation failed | Missing required field, wrong type |
| `429` | Too Many Requests | Rate limit exceeded | More than 100 requests per minute |

### Server error codes

| Code | Name | When to use | Example |
|---|---|---|---|
| `500` | Internal Server Error | Unhandled exception in handler | Database connection dropped |
| `502` | Bad Gateway | Upstream service returned invalid response | Third-party API down |
| `503` | Service Unavailable | Server is temporarily overloaded | Maintenance window |
| `504` | Gateway Timeout | Upstream service did not respond in time | Slow third-party API |

## Validation patterns

### Pydantic (FastAPI native)

```python
from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    """Validated user creation payload."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
        description="Lowercase alphanumeric with "
        "underscores",
    )
    email: str = Field(
        ...,
        description="Valid email address",
    )
    age: int | None = Field(
        None,
        ge=13,
        le=150,
        description="Must be 13 or older",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Check email format."""
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower()
```

### Marshmallow (Flask / framework-agnostic)

```python
from marshmallow import Schema, fields, validate


class CreateUserSchema(Schema):
    """Validated user creation payload."""

    username = fields.Str(
        required=True,
        validate=validate.Regexp(
            r"^[a-z0-9_]{3,30}$",
        ),
    )
    email = fields.Email(required=True)
    age = fields.Int(
        load_default=None,
        validate=validate.Range(min=13, max=150),
    )
```

### Comparison

| Feature | Pydantic | Marshmallow |
|---|---|---|
| Type hints | Native | Optional |
| FastAPI integration | Built-in | Manual |
| Serialization | `model_dump()` | `schema.dump()` |
| Custom validators | `@field_validator` | `@validates` |
| Nested models | Native class composition | `fields.Nested()` |
| Performance | Faster (Rust core in v2) | Slower (pure Python) |

## Pagination

### Cursor-based (recommended)

Best for real-time data where rows can be inserted
between pages.

```python
@app.get("/items")
async def list_items(
    cursor: str | None = None,
    limit: int = Field(default=20, ge=1, le=100),
):
    """List items with cursor pagination."""
    items, next_cursor = await db.list_items(
        after_cursor=cursor,
        limit=limit,
    )
    return {
        "items": items,
        "pagination": {
            "next_cursor": next_cursor,
            "has_more": next_cursor is not None,
        },
    }
```

### Offset-based

Simpler but can skip or duplicate rows if data changes
between requests.

```python
@app.get("/items")
async def list_items(
    offset: int = Field(default=0, ge=0),
    limit: int = Field(default=20, ge=1, le=100),
):
    """List items with offset pagination."""
    items = await db.list_items(
        offset=offset,
        limit=limit,
    )
    total = await db.count_items()
    return {
        "items": items,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total,
        },
    }
```

### Comparison

| Aspect | Cursor | Offset |
|---|---|---|
| Consistency | Stable across concurrent writes | Can skip or repeat rows |
| Deep pages | Fast (no scanning) | Slow (`OFFSET 10000` scans rows) |
| Jump to page N | Not possible | Easy (`offset = (N-1) * limit`) |
| Best for | Feeds, real-time data, large datasets | Admin dashboards, small datasets |

## Rate limiting

### Per-endpoint with slowapi (FastAPI)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


@app.get("/items")
@limiter.limit("100/minute")
async def list_items(request: Request):
    """Rate-limited item listing."""
    ...
```

### Response headers

Always include rate limit info in response headers so
clients can self-throttle.

| Header | Purpose | Example |
|---|---|---|
| `X-RateLimit-Limit` | Max requests per window | `100` |
| `X-RateLimit-Remaining` | Requests left in window | `42` |
| `X-RateLimit-Reset` | Seconds until window resets | `30` |
| `Retry-After` | Seconds to wait (on `429`) | `15` |

## CORS

### FastAPI configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://staging.example.com",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    max_age=600,
)
```

**Never use `allow_origins=["*"]` with
`allow_credentials=True`.** Browsers reject this
combination. List specific origins instead.

### Common CORS errors

| Error | Cause | Fix |
|---|---|---|
| "No Access-Control-Allow-Origin" | Origin not in allow list | Add the requesting origin |
| "Credential not supported with wildcard" | `*` origins + credentials | List specific origins |
| Preflight fails | OPTIONS method not allowed | Ensure middleware handles `OPTIONS` |

## OpenAPI / Swagger generation

### FastAPI (automatic)

FastAPI generates OpenAPI 3.0 docs automatically from
your route definitions and Pydantic models.

| URL | What it shows |
|---|---|
| `/docs` | Swagger UI (interactive) |
| `/redoc` | ReDoc (readable documentation) |
| `/openapi.json` | Raw OpenAPI schema |

### Enhancing generated docs

```python
@app.post(
    "/items",
    status_code=201,
    response_model=ItemResponse,
    summary="Create a new item",
    description="Creates an item owned by the "
    "authenticated user. Returns the created item "
    "with a generated ID.",
    responses={
        409: {
            "description": "Item with this name "
            "already exists",
        },
        422: {
            "description": "Validation error in "
            "request body",
        },
    },
)
async def create_item(payload: CreateItemRequest):
    ...
```

## Error response format

### Standard format

Use this structure for all error responses across your
API.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body validation failed",
    "details": [
      {
        "field": "email",
        "message": "Not a valid email address"
      },
      {
        "field": "quantity",
        "message": "Must be greater than 0"
      }
    ]
  }
}
```

### Error code catalog

| Code | HTTP status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | `422` | Schema validation failed |
| `NOT_FOUND` | `404` | Requested resource does not exist |
| `DUPLICATE` | `409` | Resource already exists |
| `UNAUTHORIZED` | `401` | Missing or invalid credentials |
| `FORBIDDEN` | `403` | Authenticated but not authorized |
| `RATE_LIMITED` | `429` | Too many requests |
| `INTERNAL_ERROR` | `500` | Unexpected server error |

### FastAPI exception handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Convert Pydantic errors to standard format."""
    details = [
        {
            "field": ".".join(str(x) for x in e["loc"]),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request body validation "
                "failed",
                "details": details,
            }
        },
    )
```

## Versioning strategies

| Strategy | Implementation | When to use |
|---|---|---|
| URL path | `/v1/items`, `/v2/items` | Default choice for most APIs |
| Accept header | `Accept: application/vnd.api.v2+json` | When URL cleanliness matters |
| Query parameter | `/items?version=2` | Quick prototyping |
| No versioning | Additive-only changes | Internal APIs with controlled clients |

### URL path versioning with FastAPI

```python
from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")
v2 = APIRouter(prefix="/v2")


@v1.get("/items")
async def list_items_v1():
    """V1: Returns flat list."""
    ...


@v2.get("/items")
async def list_items_v2():
    """V2: Returns paginated response."""
    ...


app.include_router(v1)
app.include_router(v2)
```

## Want to learn more?

- "What are the design principles behind these patterns?"
  -- see the **concept** template for REST conventions
  and trade-offs
- "Walk me through building an endpoint step by step" --
  see the **task** template for a guided implementation
- Run `/security` to audit your endpoints for missing
  validation, injection risks, and CORS misconfigurations
- Run `/code-quality` to check handler consistency and
  error handling patterns

## Related Topics

- **Concept**: API endpoint design -- REST conventions,
  versioning, and when to use REST vs GraphQL
- **Task**: API endpoint design -- step-by-step from
  route definition to tested endpoint
- **Quickstart**: API endpoint design -- 5-step guide to
  add a new endpoint
