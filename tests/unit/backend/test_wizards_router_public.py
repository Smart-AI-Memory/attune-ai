"""Wizards catalog router: mounts as ``router`` and stays intentionally public.

Two things are pinned here:

1. **Boot-bug regression guard.** ``backend/main.py`` mounts this module with
   ``app.include_router(wizards.router)``. The module previously exposed a
   standalone ``app = FastAPI(...)`` and *no* ``router`` attribute, so the
   backend raised ``AttributeError`` at startup. These tests assert the module
   exposes an ``APIRouter`` named ``router`` and no longer a standalone ``app``.

2. **Intentional-public contract.** Unlike the user-scoped sibling routers
   (``users``, ``subscriptions``, ``analysis``), the wizards routes return only
   static, non-sensitive capability metadata with no principal-scoped filtering.
   They are deliberately unauthenticated so a frontend can render the catalog
   before sign-in. These tests assert both routes answer 200 with no bearer
   token (and even with a forged one), documenting that the absence of auth is a
   decision, not the original oversight.

The module is loaded in isolation via ``importlib`` rather than
``import api.wizards``: the ``api`` package ``__init__`` eagerly imports the
sibling routers, whose pydantic ``EmailStr`` models require the optional
``email-validator`` extra that is absent from the worktree venv. ``wizards.py``
has zero backend-internal imports (only ``time``, ``typing``, ``fastapi``), so
loading just that file keeps the test hermetic and free of those extras.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import importlib.util
import pathlib

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

_WIZARDS_PATH = pathlib.Path(__file__).resolve().parents[3] / "backend" / "api" / "wizards.py"


def _load_wizards_module():
    """Load ``backend/api/wizards.py`` in isolation (no ``api`` package init)."""
    spec = importlib.util.spec_from_file_location("wizards_under_test", _WIZARDS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wizards_module():
    """The isolated wizards module under test."""
    return _load_wizards_module()


@pytest.fixture(scope="module")
def client(wizards_module):
    """A TestClient over a fresh app mounting only ``wizards.router``."""
    app = FastAPI()
    app.include_router(wizards_module.router)
    return TestClient(app)


class TestRouterShape:
    """The module exposes the ``router`` that ``backend/main.py`` mounts."""

    def test_exposes_apirouter_named_router(self, wizards_module):
        """``wizards.router`` exists and is an ``APIRouter`` (boot-bug guard)."""
        assert hasattr(
            wizards_module, "router"
        ), "backend/main.py mounts wizards.router; the module must expose it"
        assert isinstance(wizards_module.router, APIRouter)

    def test_no_standalone_app(self, wizards_module):
        """The old standalone ``app`` is gone (main.py owns the FastAPI app)."""
        assert not hasattr(wizards_module, "app")

    def test_routes_registered_under_prefix(self, wizards_module):
        """Both catalog routes are registered under the ``/api/wizards`` prefix."""
        paths = {route.path for route in wizards_module.router.routes}
        assert "/api/wizards" in paths
        assert "/api/wizards/{wizard_id}" in paths


class TestIntentionallyPublic:
    """The catalog routes answer without authentication, by design."""

    def test_list_public_no_auth(self, client):
        """GET /api/wizards returns the catalog with no Authorization header."""
        response = client.get("/api/wizards")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == len(body["wizards"])
        assert body["total"] > 0

    def test_detail_public_no_auth(self, client):
        """GET /api/wizards/{id} returns a wizard with no Authorization header."""
        response = client.get("/api/wizards/healthcare")
        assert response.status_code == 200
        assert response.json()["id"] == "healthcare"

    def test_detail_unknown_id_404(self, client):
        """An unknown wizard id yields 404, not a 401/403 auth challenge."""
        response = client.get("/api/wizards/does-not-exist")
        assert response.status_code == 404

    def test_forged_bearer_is_accepted(self, client):
        """A forged bearer token does not gate the public catalog (200).

        Contrast with the sibling routers, where ``require_principal`` rejects a
        forged token with 401. The wizards catalog is deliberately open, so the
        token is ignored rather than verified.
        """
        response = client.get(
            "/api/wizards",
            headers={"Authorization": "Bearer forged.not-a-real.jwt"},
        )
        assert response.status_code == 200
