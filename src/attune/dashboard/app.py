"""Agent Coordination Dashboard - FastAPI Application.

Web dashboard for monitoring all 6 Agent Coordination patterns:
1. Agent Heartbeat Tracking
2. Coordination Signals
3. State Synchronization
4. Real-Time Event Streaming
5. Human Approval Gates
6. Agent-to-LLM Feedback Loop

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from attune.telemetry import (
    ApprovalGate,
    CoordinationSignals,
    EventStreamer,
    FeedbackLoop,
    HeartbeatCoordinator,
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Empathy Agent Dashboard",
    description="Real-time monitoring dashboard for agent coordination patterns",
    version="1.0.0",
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================================
# Models
# ============================================================================


class AgentStatus(BaseModel):
    """Agent status summary."""

    agent_id: str
    status: str
    last_seen: str
    progress: float
    current_task: str


class SignalSummary(BaseModel):
    """Coordination signal summary."""

    signal_type: str
    source_agent: str
    target_agent: str
    timestamp: str
    payload: dict[str, Any]


class ApprovalRequestSummary(BaseModel):
    """Approval request summary."""

    request_id: str
    approval_type: str
    agent_id: str
    context: dict[str, Any]
    timestamp: str
    timeout_seconds: float


class QualityMetrics(BaseModel):
    """Quality feedback metrics."""

    workflow_name: str
    stage_name: str
    tier: str
    avg_quality: float
    sample_count: int
    trend: float


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve dashboard HTML."""
    html_file = static_dir / "index.html"
    if not html_file.exists():
        return """
        <html>
            <head><title>Agent Dashboard</title></head>
            <body>
                <h1>Agent Coordination Dashboard</h1>
                <p>Dashboard UI not found. Please ensure static files are built.</p>
                <p>API Documentation: <a href="/docs">/docs</a></p>
            </body>
        </html>
        """
    return html_file.read_text()


# ============================================================================
# Pattern 1: Agent Heartbeat Tracking
# ============================================================================


@app.get("/api/agents", response_model=list[AgentStatus])
async def get_active_agents():
    """Get all active agents with heartbeats."""
    try:
        coordinator = HeartbeatCoordinator()
        active_agents = coordinator.get_active_agents()

        result = []
        for agent_id in active_agents:
            heartbeat = coordinator.get_heartbeat(agent_id)
            if heartbeat:
                result.append(
                    AgentStatus(
                        agent_id=agent_id,
                        status=heartbeat.status,
                        last_seen=heartbeat.timestamp.isoformat(),
                        progress=heartbeat.progress,
                        current_task=heartbeat.current_task,
                    )
                )

        return result
    except Exception as e:
        logger.error(f"Failed to get active agents: {e}")
        return []


@app.get("/api/agents/{agent_id}")
async def get_agent_status(agent_id: str):
    """Get specific agent status."""
    try:
        coordinator = HeartbeatCoordinator()
        heartbeat = coordinator.get_heartbeat(agent_id)

        if not heartbeat:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "agent_id": agent_id,
            "status": heartbeat.status,
            "last_seen": heartbeat.timestamp.isoformat(),
            "progress": heartbeat.progress,
            "current_task": heartbeat.current_task,
            "metadata": heartbeat.metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Pattern 2: Coordination Signals
# ============================================================================


@app.get("/api/signals", response_model=list[SignalSummary])
async def get_recent_signals(limit: int = 50):
    """Get recent coordination signals."""
    try:
        signals = CoordinationSignals()
        recent = signals.get_recent_signals(limit=limit)

        return [
            SignalSummary(
                signal_type=sig.signal_type,
                source_agent=sig.source_agent,
                target_agent=sig.target_agent,
                timestamp=sig.timestamp.isoformat(),
                payload=sig.payload,
            )
            for sig in recent
        ]
    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        return []


@app.get("/api/signals/{agent_id}")
async def get_agent_signals(agent_id: str, limit: int = 20):
    """Get signals for specific agent."""
    try:
        signals = CoordinationSignals()
        agent_signals = signals.get_signals_for_agent(agent_id, limit=limit)

        return [
            {
                "signal_type": sig.signal_type,
                "source_agent": sig.source_agent,
                "target_agent": sig.target_agent,
                "timestamp": sig.timestamp.isoformat(),
                "payload": sig.payload,
            }
            for sig in agent_signals
        ]
    except Exception as e:
        logger.error(f"Failed to get agent signals: {e}")
        return []


# ============================================================================
# Pattern 4: Real-Time Event Streaming
# ============================================================================


@app.get("/api/events")
async def get_recent_events(event_type: str | None = None, limit: int = 100):
    """Get recent events from streams."""
    try:
        streamer = EventStreamer()

        if event_type:
            events = list(streamer.get_recent_events(event_type, limit=limit))
        else:
            # Get events from multiple common streams
            all_events = []
            for evt_type in ["agent_heartbeat", "coordination_signal", "workflow_progress"]:
                events = list(streamer.get_recent_events(evt_type, limit=20))
                all_events.extend(events)

            # Sort by timestamp and limit
            all_events.sort(key=lambda e: e.timestamp, reverse=True)
            events = all_events[:limit]

        return [
            {
                "event_id": evt.event_id,
                "event_type": evt.event_type,
                "timestamp": evt.timestamp.isoformat(),
                "data": evt.data,
                "source": evt.source,
            }
            for evt in events
        ]
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        return []


# ============================================================================
# Pattern 5: Human Approval Gates
# ============================================================================


@app.get("/api/approvals", response_model=list[ApprovalRequestSummary])
async def get_pending_approvals():
    """Get pending approval requests."""
    try:
        gate = ApprovalGate()
        pending = gate.get_pending_approvals()

        return [
            ApprovalRequestSummary(
                request_id=req.request_id,
                approval_type=req.approval_type,
                agent_id=req.agent_id,
                context=req.context,
                timestamp=req.timestamp.isoformat(),
                timeout_seconds=req.timeout_seconds,
            )
            for req in pending
        ]
    except Exception as e:
        logger.error(f"Failed to get pending approvals: {e}")
        return []


@app.post("/api/approvals/{request_id}/approve")
async def approve_request(request_id: str, reason: str = "Approved via dashboard"):
    """Approve a pending request."""
    try:
        gate = ApprovalGate()
        success = gate.respond_to_approval(
            request_id=request_id, approved=True, responder="dashboard", reason=reason
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to record approval")

        return {"status": "approved", "request_id": request_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/{request_id}/reject")
async def reject_request(request_id: str, reason: str = "Rejected via dashboard"):
    """Reject a pending request."""
    try:
        gate = ApprovalGate()
        success = gate.respond_to_approval(
            request_id=request_id, approved=False, responder="dashboard", reason=reason
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to record rejection")

        return {"status": "rejected", "request_id": request_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Pattern 6: Agent-to-LLM Feedback Loop
# ============================================================================


@app.get("/api/feedback/workflows")
async def get_workflow_quality():
    """Get quality metrics for workflows."""
    try:
        feedback = FeedbackLoop()

        # Get stats for known workflows (in production, this would query all workflows)
        workflows = ["code-review", "test-generation", "refactoring"]
        results = []

        for workflow in workflows:
            for stage in ["analysis", "generation", "validation"]:
                for tier in ["cheap", "capable", "premium"]:
                    stats = feedback.get_quality_stats(workflow, stage, tier=tier)
                    if stats and stats.sample_count > 0:
                        results.append(
                            QualityMetrics(
                                workflow_name=workflow,
                                stage_name=stage,
                                tier=tier,
                                avg_quality=stats.avg_quality,
                                sample_count=stats.sample_count,
                                trend=stats.recent_trend,
                            )
                        )

        return results
    except Exception as e:
        logger.error(f"Failed to get workflow quality: {e}")
        return []


@app.get("/api/feedback/underperforming")
async def get_underperforming_stages(threshold: float = 0.7):
    """Get underperforming workflow stages."""
    try:
        feedback = FeedbackLoop()

        # Check known workflows
        workflows = ["code-review", "test-generation", "refactoring"]
        all_underperforming = []

        for workflow in workflows:
            underperforming = feedback.get_underperforming_stages(
                workflow, quality_threshold=threshold
            )
            for stage_name, stats in underperforming:
                all_underperforming.append(
                    {
                        "workflow_name": workflow,
                        "stage_name": stage_name,
                        "avg_quality": stats.avg_quality,
                        "sample_count": stats.sample_count,
                        "min_quality": stats.min_quality,
                        "max_quality": stats.max_quality,
                        "trend": stats.recent_trend,
                    }
                )

        # Sort by worst quality
        all_underperforming.sort(key=lambda x: x["avg_quality"])

        return all_underperforming
    except Exception as e:
        logger.error(f"Failed to get underperforming stages: {e}")
        return []


# ============================================================================
# System Health
# ============================================================================


@app.get("/api/health")
async def get_system_health():
    """Get overall system health status."""
    try:
        # Check if Redis is available
        coordinator = HeartbeatCoordinator()
        has_redis = coordinator.memory is not None

        # Get counts
        active_agents = len(coordinator.get_active_agents()) if has_redis else 0

        gate = ApprovalGate()
        pending_approvals = len(gate.get_pending_approvals()) if has_redis else 0

        return {
            "status": "healthy" if has_redis else "degraded",
            "redis_available": has_redis,
            "active_agents": active_agents,
            "pending_approvals": pending_approvals,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("Health check failed")
        return {
            "status": "unhealthy",
            "redis_available": False,
            "error": "Health check failed. Check server logs for details.",
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# WebSocket for Real-Time Updates
# ============================================================================


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Client disconnected


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive ping to keep connection alive
            _ = await websocket.receive_text()

            # Send updates (in production, this would stream from Redis)
            coordinator = HeartbeatCoordinator()
            active_agents = coordinator.get_active_agents()

            await websocket.send_json(
                {"type": "agent_update", "agents": [{"agent_id": aid} for aid in active_agents]}
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# Run Server
# ============================================================================


def run_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """Run the dashboard server.

    Args:
        host: Host to bind to
        port: Port to bind to

    Example:
        >>> from attune.dashboard import run_dashboard
        >>> run_dashboard(host="0.0.0.0", port=8080)
    """
    import uvicorn

    logger.info(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
