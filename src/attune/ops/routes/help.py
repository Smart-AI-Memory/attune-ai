"""Read-only API for the dashboard's /help page.

Routes:

  - GET /api/help/              → corpus summary (features, stats)
  - GET /api/help/search?q=…    → ranked search hits
  - GET /api/help/feature/<slug> → one feature's kinds + summary
  - GET /api/help/template/<feature>/<kind> → one template (metadata + body)
  - GET /api/help/gaps          → coverage gaps + stale templates

All GET-only. Slugs are validated against ``[a-z][a-z0-9-]*`` to
prevent path-traversal in the template route. The data module
swallows internal errors and returns empty results, so the routes
themselves only convert dataclasses → JSON.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from attune.ops import help_data

router = APIRouter()


@router.get("/api/help/")
async def help_index(request: Request) -> JSONResponse:
    """Top-level summary — features list + corpus stats."""
    cfg = request.app.state.config
    features = help_data.list_features(cfg)
    return JSONResponse(
        {
            "features": [f.to_dict() for f in features],
            "total_features": len(features),
            "total_templates": sum(len(f.kinds) for f in features),
            "stale_count": sum(f.stale_count for f in features),
            "incomplete_count": sum(1 for f in features if not f.is_complete),
        }
    )


@router.get("/api/help/search")
async def help_search(request: Request, q: str = "", limit: int = 20) -> JSONResponse:
    """Ranked search hits.

    Empty query → empty list (not an error). limit is clamped to 50.
    """
    limit = max(1, min(50, int(limit)))
    cfg = request.app.state.config
    hits = help_data.search(cfg, q, limit=limit)
    return JSONResponse(
        {
            "query": q,
            "limit": limit,
            "hits": [h.to_dict() for h in hits],
        }
    )


@router.get("/api/help/feature/{slug}")
async def help_feature(request: Request, slug: str) -> JSONResponse:
    """All kinds available for a single feature."""
    if not help_data._safe_slug(slug):
        raise HTTPException(status_code=400, detail="invalid feature slug")
    cfg = request.app.state.config
    features = {f.name: f for f in help_data.list_features(cfg)}
    feature = features.get(slug)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"feature not found: {slug}")
    return JSONResponse(feature.to_dict())


@router.get("/api/help/template/{feature}/{kind}")
async def help_template(request: Request, feature: str, kind: str) -> JSONResponse:
    """One template — metadata + full markdown body."""
    if not help_data._safe_slug(feature):
        raise HTTPException(status_code=400, detail="invalid feature slug")
    if not help_data._safe_slug(kind):
        raise HTTPException(status_code=400, detail="invalid kind slug")
    cfg = request.app.state.config
    rec = help_data.get_template(cfg, feature, kind)
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=f"template not found: {feature}/{kind}",
        )
    return JSONResponse(rec.to_dict())


@router.get("/api/help/gaps")
async def help_gaps(request: Request) -> JSONResponse:
    """Coverage gaps + stale templates — admin-tools surface."""
    cfg = request.app.state.config
    return JSONResponse(help_data.coverage_gaps(cfg).to_dict())


@router.get("/api/help/featured")
async def help_featured(request: Request) -> JSONResponse:
    """Curated featured-topics list for the home page."""
    cfg = request.app.state.config
    feats = help_data.featured_topics(cfg)
    return JSONResponse({"featured": [f.to_dict() for f in feats]})


@router.get("/api/help/recent")
async def help_recent(request: Request, limit: int = 5) -> JSONResponse:
    """Recently-regenerated templates."""
    limit = max(1, min(20, int(limit)))
    cfg = request.app.state.config
    recs = help_data.recently_regenerated(cfg, limit=limit)
    return JSONResponse({"recent": [r.to_dict() for r in recs]})
