---
type: quickstart
name: task-api-endpoint-design
tags: [api, python, rest, patterns]
source: developer-guidance
---

# Quickstart: Add a new API endpoint

Five steps from route definition to tested endpoint.

## 1. Define the route

Pick the HTTP method that matches the operation.

```python
from fastapi import FastAPI

app = FastAPI()


@app.post("/items", status_code=201)
async def create_item(payload: CreateItemRequest):
    """Create a new item."""
    ...
```

Use `GET` to read, `POST` to create, `PUT` to replace,
`PATCH` to update, `DELETE` to remove.

## 2. Validate the request with Pydantic

```python
from pydantic import BaseModel, Field


class CreateItemRequest(BaseModel):
    """Request body for item creation."""

    name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    tags: list[str] = Field(default_factory=list)
```

Pydantic returns `422` automatically if the body is
invalid. You do not need to write validation logic for
type and constraint checks.

## 3. Return a consistent error format

```python
from fastapi.responses import JSONResponse


def error_response(
    status_code: int, code: str, message: str,
) -> JSONResponse:
    """Standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieve an item by ID."""
    item = await db.get_item(item_id)
    if item is None:
        return error_response(404, "NOT_FOUND", "Item not found")
    return item
```

Use the same `error` shape for every error across your
API.

## 4. Protect with authentication

```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> User:
    """Validate bearer token."""
    user = await verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@app.post("/items", status_code=201)
async def create_item(
    payload: CreateItemRequest,
    user: User = Depends(get_current_user),
):
    """Create item (authenticated)."""
    return await db.create_item(owner_id=user.id, **payload.model_dump())
```

## 5. Write a test

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient, auth_headers: dict):
    """Test item creation returns 201."""
    response = await client.post(
        "/items",
        json={"name": "Widget", "quantity": 5},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Widget"


@pytest.mark.asyncio
async def test_create_item_invalid(client: AsyncClient, auth_headers: dict):
    """Test invalid input returns 422."""
    response = await client.post(
        "/items",
        json={"name": "", "quantity": -1},
        headers=auth_headers,
    )
    assert response.status_code == 422
```

## Verify

Run `/security` on your endpoint module to check for
input validation gaps and injection risks.

Run `/code-quality` to verify consistent error handling
and type hints across your handlers.

## Want to learn more?

- "Walk me through the full implementation process" --
  see the **task** template for a complete guide with
  authentication and business validation
- "Show me all status codes and patterns" -- see the
  **reference** template for the full catalog
- "What are the design principles?" -- see the
  **concept** template for REST conventions and
  versioning strategies

## Related Topics

- **Concept**: API endpoint design -- REST conventions,
  versioning, and when to choose REST vs GraphQL
- **Task**: API endpoint design -- full implementation
  from route to tested endpoint with auth
- **Reference**: API endpoint design -- all status codes,
  pagination, rate limiting, CORS, and OpenAPI patterns
