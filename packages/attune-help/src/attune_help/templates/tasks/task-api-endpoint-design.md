---
type: task
name: task-api-endpoint-design
tags: [api, python, rest, patterns]
source: developer-guidance
---

# Task: Design and implement an API endpoint

Build a production-ready API endpoint with request
validation, error handling, authentication, and tests.
This guide uses FastAPI but the patterns apply to Flask,
Django REST Framework, and other Python web frameworks.

## Prerequisites

- A Python web framework installed (FastAPI, Flask, etc.)
- Familiarity with HTTP methods and status codes
- Pydantic installed (comes with FastAPI; install
  separately for Flask)

## Steps

### 1. Define the route and method

Choose the HTTP method based on what the endpoint does.

| You want to... | Method | Route pattern |
|---|---|---|
| List items | `GET` | `/items` |
| Get one item | `GET` | `/items/{item_id}` |
| Create an item | `POST` | `/items` |
| Replace an item | `PUT` | `/items/{item_id}` |
| Partially update | `PATCH` | `/items/{item_id}` |
| Delete an item | `DELETE` | `/items/{item_id}` |

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.post("/items", status_code=201)
async def create_item(payload: CreateItemRequest):
    """Create a new item."""
    ...
```

Use nouns for resources (`/items`, `/users`), not verbs
(`/createItem`). Use plural nouns consistently.

### 2. Define request and response models

Use Pydantic models for both input validation and
response serialization. This gives you automatic type
checking, documentation, and error messages.

```python
from pydantic import BaseModel, Field, EmailStr


class CreateItemRequest(BaseModel):
    """Request body for creating an item."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the item",
    )
    description: str | None = Field(
        None,
        max_length=2000,
        description="Optional long description",
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Must be a positive integer",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Up to 10 tags",
    )


class ItemResponse(BaseModel):
    """Response body for a single item."""

    id: str
    name: str
    description: str | None
    quantity: int
    tags: list[str]
    created_at: str
```

Pydantic validates automatically. If `quantity` is `-1`,
FastAPI returns `422 Unprocessable Entity` with a clear
error message before your handler code runs.

### 3. Implement consistent error responses

Define a standard error format and use it everywhere.

```python
from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    """Return a standardized error response."""
    body = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(
        status_code=status_code,
        content=body,
    )


@app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieve a single item by ID."""
    item = await db.get_item(item_id)
    if item is None:
        return error_response(
            404,
            "NOT_FOUND",
            f"Item {item_id} does not exist",
        )
    return ItemResponse(**item)
```

### 4. Add authentication middleware

Protect endpoints that require an authenticated user.

```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> User:
    """Validate the bearer token and return the user."""
    token = credentials.credentials
    user = await verify_token(token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )
    return user


@app.post("/items", status_code=201)
async def create_item(
    payload: CreateItemRequest,
    user: User = Depends(get_current_user),
):
    """Create a new item (authenticated)."""
    item = await db.create_item(
        owner_id=user.id,
        **payload.model_dump(),
    )
    return ItemResponse(**item)
```

### 5. Add business validation

Schema validation catches type errors. Business
validation catches logic errors.

```python
@app.post("/items", status_code=201)
async def create_item(
    payload: CreateItemRequest,
    user: User = Depends(get_current_user),
):
    """Create a new item with business rules."""
    # Business validation
    existing = await db.get_item_by_name(
        owner_id=user.id,
        name=payload.name,
    )
    if existing:
        return error_response(
            409,
            "DUPLICATE",
            f"An item named '{payload.name}' already "
            f"exists",
        )

    if not user.can_create_items:
        return error_response(
            403,
            "FORBIDDEN",
            "Your plan does not allow creating items",
        )

    item = await db.create_item(
        owner_id=user.id,
        **payload.model_dump(),
    )
    return ItemResponse(**item)
```

### 6. Write tests

Test both the happy path and every error branch.

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_item_success(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test successful item creation."""
    response = await client.post(
        "/items",
        json={
            "name": "Widget",
            "quantity": 5,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["quantity"] == 5
    assert "id" in data


@pytest.mark.asyncio
async def test_create_item_validation_error(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that invalid input returns 422."""
    response = await client.post(
        "/items",
        json={"name": "", "quantity": -1},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_item_unauthenticated(
    client: AsyncClient,
):
    """Test that missing auth returns 401."""
    response = await client.post(
        "/items",
        json={"name": "Widget", "quantity": 5},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_item_not_found(
    client: AsyncClient,
    auth_headers: dict,
):
    """Test that missing item returns 404."""
    response = await client.get(
        "/items/nonexistent",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
```

### 7. Review with tooling

Run `/security` on your endpoint module to detect:

- Missing input validation on path or query parameters
- Endpoints that accept user input without sanitization
- Hardcoded credentials or insecure configurations

Run `/code-quality` on your handler functions to check:

- Consistent error response patterns
- Proper exception handling in async handlers
- Missing type hints or docstrings

## Verification

After implementing the endpoint:

- [ ] Route uses the correct HTTP method for the
      operation
- [ ] Request body is validated with a Pydantic model
- [ ] Error responses use a consistent JSON format
- [ ] Authentication is enforced where required
- [ ] Business validation returns appropriate status
      codes (`409`, `403`, etc.)
- [ ] Tests cover happy path, validation errors, auth
      errors, and not-found cases
- [ ] OpenAPI docs generate correctly (`/docs` in
      FastAPI)

## Want to learn more?

- "What are the REST conventions behind these choices?"
  -- see the **concept** template for design principles
- "Show me all status codes and validation patterns" --
  see the **reference** template for the full catalog
- "I just need to add one endpoint quickly" -- see the
  **quickstart** for a 5-step minimal guide

## Related Topics

- **Concept**: API endpoint design -- REST conventions,
  versioning strategies, and when to use REST vs GraphQL
- **Reference**: API endpoint design -- all status codes,
  pagination, rate limiting, CORS, and OpenAPI patterns
- **Quickstart**: API endpoint design -- 5-step guide
  from route to test
