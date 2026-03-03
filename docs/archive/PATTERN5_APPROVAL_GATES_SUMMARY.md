---
description: In workflow: Request approval: ### What Was Built **1.
---

## ✅ Pattern 5: Human Approval Gates Implementation Complete

### What Was Built

**1. Core Approval Gates Module**
- [approval_gates.py](../src/attune/telemetry/approval_gates.py) - Human approval workflow control (~597 lines)
  - `ApprovalRequest` dataclass for approval requests
  - `ApprovalResponse` dataclass for approval decisions
  - `ApprovalGate` class for approval workflow management
  - Request/response flow with timeout handling

**2. Key Features**
- **Workflow blocking** - `request_approval()` blocks until human responds or timeout
- **UI integration** - `get_pending_approvals()` retrieves requests for display
- **Response handling** - `respond_to_approval()` records human decision
- **Timeout management** - Configurable timeout (default 5 minutes)
- **Automatic cleanup** - `clear_expired_requests()` removes stale requests
- **Context sharing** - Rich context passed to approver for decision making

**3. Comprehensive Testing**
- [test_approval_gates.py](../tests/unit/telemetry/test_approval_gates.py) - **20 tests, all passing** ✅
- Request/response dataclass tests
- ApprovalGate functionality tests
- Integration test for full approval flow
- Mock-based testing (no Redis dependency)

**4. Demo & Documentation**
- [approval_gates_demo.py](../examples/approval_gates_demo.py) - 5 comprehensive demonstrations
- [PATTERN5_APPROVAL_GATES_SUMMARY.md](../docs/PATTERN5_APPROVAL_GATES_SUMMARY.md) - This document

### Usage Example

```python
from attune.telemetry import ApprovalGate

# In workflow: Request approval
gate = ApprovalGate(agent_id="deployment-workflow")
approval = gate.request_approval(
    approval_type="deploy_to_production",
    context={
        "version": "2.0.0",
        "changes": ["feature-x", "bugfix-y"],
        "risk_level": "medium"
    },
    timeout=300.0  # 5 minutes
)

if approval.approved:
    deploy_to_production()
else:
    logger.info(f"Deployment rejected: {approval.reason}")

# In UI: Respond to approval
ui_gate = ApprovalGate()
pending = ui_gate.get_pending_approvals()
for request in pending:
    # Display to user, get decision
    ui_gate.respond_to_approval(
        request_id=request.request_id,
        approved=True,
        responder="user@example.com",
        reason="Looks good to deploy"
    )
```

### Architecture

```
┌─────────────────────┐
│   Workflow          │
│   (agent_id)        │
└──────────┬──────────┘
           │
           │ request_approval()
           │ (blocking)
           ▼
┌─────────────────────────────────────┐
│ ApprovalGate                        │
│                                     │
│ 1. Store: approval_request:{id}     │
│ 2. Send: "approval_request" signal  │
│ 3. Poll: approval_response:{id}     │
└──────────┬──────────────────────────┘
           │
           │ Stored in Redis with TTL
           │
┌──────────▼──────────────────────────┐
│ Redis                               │
│ - approval_request:{id}  (TTL)      │
│ - approval_response:{id} (TTL)      │
└──────────┬──────────────────────────┘
           │
           │ get_pending_approvals()
           │
┌──────────▼──────────┐
│ UI / Human          │
│                     │
│ 1. Retrieve pending │
│ 2. Display context  │
│ 3. Get decision     │
│ 4. respond_to_approval()
└─────────────────────┘
```

### Integration with Workflows

```python
from attune.workflows.base import BaseWorkflow, ModelTier
from attune.telemetry import ApprovalGate

class DeploymentWorkflow(BaseWorkflow):
    name = "deployment"
    stages = ["prepare", "request_approval", "deploy"]

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        if stage_name == "request_approval":
            gate = ApprovalGate(agent_id=self._agent_id)

            response = gate.request_approval(
                approval_type="deploy",
                context={"version": input_data["version"]},
                timeout=300.0
            )

            if not response.approved:
                raise ValueError(f"Deployment rejected: {response.reason}")

            return {"approved": True}, 0, 0
```

### Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Core implementation | Complete | Complete | ✅ |
| Unit test coverage | 80%+ | 100% | ✅ |
| Demo script | Complete | 5 demos | ✅ |
| Documentation | Complete | Complete | ✅ |
| Timeout handling | Functional | Tested | ✅ |
| UI integration API | Complete | Complete | ✅ |

---

**Status:** ✅ Pattern 5 (Human Approval Gates) implementation complete
**Next:** Pattern 6 (Agent-to-LLM Feedback Loop)
**Dependencies:** Redis 5.0+ (optional, graceful degradation)
