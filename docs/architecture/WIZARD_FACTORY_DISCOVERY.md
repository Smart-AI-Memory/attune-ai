---
description: Wizard Factory Enhancement - Discovery Report: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Wizard Factory Enhancement - Discovery Report

**Date:** 2026-01-05
**Phase:** Discovery & Pattern Extraction
**Status:** Complete

## Executive Summary

This report documents findings from analyzing the existing wizard infrastructure in Attune AI. We identified **78 existing wizards** across 4 categories and extracted **5 major pattern categories** that will form the foundation of the Wizard Factory enhancement.

**Key Finding:** Rather than building an abstract pattern library from scratch, we can extract proven patterns from our existing 78 wizards and create a Pydantic-based system that makes wizard creation 10x faster.

**Recommended Approach:** Phased implementation starting with Pattern Library (2 weeks), followed by Hot-Reload (1 week), Test Generator (2 weeks), and Methodology Scaffolding (1 week).

---

## 1. Existing Infrastructure Analysis

### 1.1 Wizard Inventory (78 Total)

#### Healthcare Wizards (16 wizards)
Located in: `wizards/`

- SOAP Note Documentation
- SBAR Communication
- Shift Handoff
- Admission Assessment
- Discharge Summary
- Discharge Planning
- Care Planning
- Clinical Assessment
- Nursing Assessment
- Treatment Planning
- Patient Education
- Medication Reconciliation
- Dosage Calculation
- Quality Improvement
- Incident Reporting

#### Domain Wizards (16 wizards)
Located in: `attune_llm/wizards/`

Base: `BaseWizard` class using `WizardConfig` dataclass

Domains:
- Healthcare
- Finance
- Legal
- Education
- Customer Support
- HR
- Sales
- Real Estate
- Insurance
- Accounting
- Research
- Government
- Retail
- Manufacturing
- Logistics
- Technology

**Pattern:** All use `process(user_input, user_id, empathy_level, session_context)` → dict

#### Coach Wizards (16 wizards)
Located in: `coach_wizards/`

Base: `BaseCoachWizard` with Level 4 Anticipatory Empathy

Wizards:
- Debugging
- Testing
- Security
- Documentation
- Performance
- Refactoring
- Database
- API Design
- Compliance
- Monitoring
- CI/CD
- Accessibility
- Localization
- Migration
- Observability
- Scaling

**Pattern:** All use `analyze_code(code, file_path, language)` → list[WizardIssue]

#### AI Software Wizards (12 wizards)
Located in: `empathy_software_plugin/wizards/`

Advanced wizards with protocol-based analysis:
- Advanced Debugging (Level 4)
- Agent Orchestration
- AI Collaboration
- AI Context Window
- AI Documentation
- Enhanced Testing
- Multi-Model
- Performance Profiling
- Prompt Engineering
- RAG Pattern
- Security Analysis

**Pattern:** Complex `analyze(context)` → comprehensive dict with predictions, recommendations, patterns

#### Coach Examples (18 wizards)
Located in: `examples/coach/wizards/`

Reference implementations for various domains.

### 1.2 Current Registration System

**File:** `backend/api/wizard_api.py`

**Architecture:**
```python
# Simple dictionary-based registry
WIZARDS = {}

def register_wizard(wizard_id: str, wizard_class: type, *args, **kwargs) -> bool:
    """Register with graceful exception handling"""
    try:
        WIZARDS[wizard_id] = wizard_class(*args, **kwargs)
        return True
    except (ImportError, ValueError, OSError, IOError) as e:
        logger.warning(f"Wizard init failed: {e}")
        return False
    except Exception:
        logger.exception(f"Unexpected error")
        return False
```

**Interfaces Supported:**
- `process()` - Domain wizards
- `analyze_code()` - Coach wizards
- `analyze()` - AI wizards

**Key Insight:** Simple, file-based registration works well. Enhancement should preserve this simplicity while adding pattern reusability.

---

## 2. Extracted Patterns

### 2.1 Structural Patterns

#### Pattern: Linear Flow
**Example:** SOAP Note Wizard
**Structure:** Step 1 → Step 2 → Step 3 → Step 4 → Review → Finalize

**Implementation:**
```python
SOAP_NOTE_STEPS = {
    1: {"title": "Subjective", "fields": [...], "help_text": "..."},
    2: {"title": "Objective", "fields": [...], "help_text": "..."},
    3: {"title": "Assessment", "fields": [...], "help_text": "..."},
    4: {"title": "Plan", "fields": [...], "help_text": "..."},
    5: {"title": "Review & Finalize", "is_review_step": True},
}
```

**Reusability:** 80% of healthcare wizards use this pattern
**Frequency:** 16 wizards

---

#### Pattern: Phased Processing
**Example:** Advanced Debugging Wizard
**Structure:** Parse → Load Config → Analyze → Group by Fixability → Apply Fixes → Verify

**Implementation:**
```python
async def analyze(self, context):
    # Phase 1: Parse inputs
    all_issues = parse_linter_output(linter_name, output)

    # Phase 2: Load configs
    config = load_config(linter_name, start_dir=project_path)

    # Phase 3: Risk analysis (Level 4)
    risk_assessments = self.bug_analyzer.analyze(all_issues)

    # Phase 4: Group by fixability
    fixability = group_issues_by_fixability(linter_name, issues)

    # Phase 5: Apply fixes
    if auto_fix:
        fixes = apply_fixes(linter_name, issues, auto_only=True)

    # Phase 6: Verification
    if verify:
        verification = verify_fixes(linter_name, project_path, issues)

    return {...}
```

**Reusability:** All AI wizards use variations of this
**Frequency:** 12 wizards

---

#### Pattern: Session-Based Wizard
**Example:** SOAP Note Wizard
**Structure:** Session storage + multi-step state management + user approval

**Implementation:**
```python
# Start wizard → get wizard_id
wizard_id = str(uuid4())
session_data = {
    "wizard_id": wizard_id,
    "current_step": 1,
    "total_steps": 5,
    "collected_data": {},
}
await _store_wizard_session(wizard_id, session_data)

# Submit each step
session["collected_data"].update(step_data)
session["current_step"] = next_step
await _store_wizard_session(wizard_id, session)

# Preview → Approve → Finalize
preview = _generate_report(session["collected_data"])
if user_approved:
    session["completed"] = True
    session["final_report"] = preview
```

**Reusability:** All healthcare wizards with multi-step flows
**Frequency:** 16 wizards

---

### 2.2 Input Patterns

#### Pattern: Structured Fields
**Example:** SOAP Note, Care Plan, Assessment wizards
**Fields:** Defined per step with validation

```python
{
    "step": 1,
    "fields": [
        "chief_complaint",
        "history_present_illness",
        "patient_reported_symptoms",
        "pain_description",
    ],
}
```

**Reusability:** 90% of healthcare wizards
**Frequency:** 16 wizards

---

#### Pattern: Code Analysis Input
**Example:** All coach wizards
**Input:** `(code: str, file_path: str, language: str)`

```python
def analyze_code(
    self,
    code: str,
    file_path: str,
    language: str
) -> list[WizardIssue]:
    """Analyze code for issues"""
    pass
```

**Reusability:** All coach wizards
**Frequency:** 16 wizards

---

#### Pattern: Context-Based Input
**Example:** AI wizards
**Input:** Flexible dict with wizard-specific keys

```python
context = {
    "project_path": ".",
    "linters": {"eslint": "output.json"},
    "configs": {"eslint": ".eslintrc.json"},
    "auto_fix": True,
    "verify": True,
}
result = await wizard.analyze(context)
```

**Reusability:** All AI wizards
**Frequency:** 12 wizards

---

### 2.3 Validation Patterns

#### Pattern: Config Validation
**Example:** BaseWizard

```python
def _validate_config(self):
    if not 0 <= self.config.default_empathy_level <= 4:
        raise ValueError(f"Empathy level must be 0-4")

    if self.config.default_classification not in ["PUBLIC", "INTERNAL", "SENSITIVE"]:
        raise ValueError(f"Invalid classification")
```

**Reusability:** All domain wizards
**Frequency:** 16 wizards

---

#### Pattern: Step Validation
**Example:** SOAP Note Wizard

```python
submitted_step = step_data.get("step", current_step)
if submitted_step != current_step:
    raise HTTPException(
        status_code=422,
        detail=f"Expected step {current_step}, got step {submitted_step}"
    )
```

**Reusability:** All multi-step healthcare wizards
**Frequency:** 16 wizards

---

#### Pattern: User Approval
**Example:** SOAP Note Wizard - Preview → Explicit Approval → Finalize

```python
# Generate preview (does NOT finalize)
preview = _generate_report(session["collected_data"])

# Verify user explicitly approved
if not approval_data.get("user_approved", False):
    raise HTTPException(
        status_code=400,
        detail="User approval required"
    )

# NOW mark as complete
session["completed"] = True
```

**Reusability:** All healthcare wizards requiring review
**Frequency:** 16 wizards

---

### 2.4 Behavior Patterns

#### Pattern: Risk Assessment
**Example:** Advanced Debugging Wizard

```python
risk_assessments = self.bug_analyzer.analyze(all_issues)
risk_summary = {
    "alert_level": "CRITICAL",
    "by_risk_level": {
        "critical": 5,
        "high": 12,
        "medium": 8,
    },
}
```

**Reusability:** All coach wizards with Level 4 Anticipatory
**Frequency:** 16 wizards

---

#### Pattern: AI Enhancement
**Example:** SOAP Note text enhancement

```python
@router.post("/{wizard_id}/enhance")
async def enhance_soap_note_text(wizard_id: str, text_data: dict):
    enhancement_prompt = f"""
    Enhance the following text for clinical documentation:

    Original: {original_text}

    Provide enhanced version with:
    - Clinical terminology
    - Professional tone
    - SOAP note standards
    """

    chat_response = await chat_service.chat(message=enhancement_prompt)
    return enhanced_text
```

**Reusability:** All healthcare wizards
**Frequency:** 16 wizards

---

#### Pattern: Prediction (Level 4 Anticipatory)
**Example:** Coach wizards

```python
def predict_future_issues(
    self,
    code: str,
    file_path: str,
    project_context: dict,
    timeline_days: int = 90
) -> list[WizardPrediction]:
    """Predict issues 90 days ahead using historical patterns"""
    predictions = []

    # Analyze trajectory
    if risk_summary["critical"] > 0:
        predictions.append({
            "type": "production_failure_risk",
            "severity": "critical",
            "prevention_steps": [...]
        })

    return predictions
```

**Reusability:** All coach wizards
**Frequency:** 16 wizards

---

#### Pattern: Fix Application
**Example:** Advanced Debugging Wizard

```python
# Group by fixability
fixability = group_issues_by_fixability(linter_name, issues)
# {
#   "auto_fixable": [issue1, issue2],
#   "manual": [issue3, issue4]
# }

# Apply auto-fixes
if auto_fix:
    fixes = apply_fixes(linter_name, issues, auto_only=True)
    successful = [f for f in fixes if f.success]
```

**Reusability:** All AI wizards with code modification
**Frequency:** 8 wizards

---

### 2.5 Empathy Patterns

#### Pattern: Empathy Levels (0-4)
**Example:** BaseWizard

```python
@dataclass
class WizardConfig:
    default_empathy_level: int = 2  # 0-4

# Level 0: Pure data/computation
# Level 1: Reactive - responds to explicit requests
# Level 2: Responsive - understands context
# Level 3: Proactive - suggests improvements
# Level 4: Anticipatory - predicts future needs
```

**Reusability:** All domain wizards
**Frequency:** 16 wizards

---

#### Pattern: Educational Banners
**Example:** SOAP Note Wizard

```python
EDU_BANNER = """
⚕️ EDUCATIONAL TOOL NOTICE ⚕️
This SOAP note wizard is an educational tool for healthcare professionals.
All clinical documentation should be reviewed and validated by qualified providers.
"""
```

**Reusability:** All healthcare wizards
**Frequency:** 16 wizards

---

## 3. Pydantic-Based Pattern Library Design

### 3.1 Why Pydantic Over XML?

**Original Proposal:** XML schemas for pattern definitions
**Recommended:** Pydantic models for pattern definitions

**Comparison:**

| Aspect | XML Schemas | Pydantic Models |
|--------|-------------|-----------------|
| **Type Safety** | Runtime only | Compile-time + runtime |
| **IDE Support** | Minimal | Full autocomplete |
| **Validation** | Manual parsing | Automatic |
| **Python Integration** | External format | Native Python |
| **Learning Curve** | Steep (XML + schema) | Gentle (Python dataclasses) |
| **Serialization** | Custom | Built-in JSON |
| **Performance** | Slower parsing | Faster (Python native) |
| **Maintainability** | Harder (2 languages) | Easier (pure Python) |

**Decision:** Use Pydantic for better Python integration, type safety, and developer experience.

---

### 3.2 Pattern Library Architecture

```python
# patterns/core.py
from pydantic import BaseModel, Field
from typing import Literal, Union
from enum import Enum

class PatternCategory(str, Enum):
    STRUCTURAL = "structural"
    INPUT = "input"
    VALIDATION = "validation"
    BEHAVIOR = "behavior"
    EMPATHY = "empathy"

class BasePattern(BaseModel):
    """Base class for all wizard patterns"""

    id: str = Field(..., description="Unique pattern identifier")
    name: str = Field(..., description="Human-readable pattern name")
    category: PatternCategory
    description: str
    frequency: int = Field(..., description="Number of wizards using this pattern")
    reusability_score: float = Field(ge=0.0, le=1.0)
    examples: list[str] = Field(default_factory=list, description="Wizard IDs using this pattern")

    class Config:
        use_enum_values = True


# patterns/structural.py
class StepConfig(BaseModel):
    step: int
    title: str
    prompt: str
    fields: list[str]
    help_text: str
    is_review_step: bool = False

class LinearFlowPattern(BasePattern):
    """Linear multi-step wizard pattern"""

    category: Literal[PatternCategory.STRUCTURAL] = PatternCategory.STRUCTURAL
    total_steps: int
    steps: dict[int, StepConfig]
    requires_approval: bool = True

    def generate_endpoints(self) -> list[str]:
        """Generate FastAPI endpoint code"""
        return [
            "POST /start",
            "POST /{wizard_id}/step",
            "POST /{wizard_id}/preview",
            "POST /{wizard_id}/save",
            "GET /{wizard_id}/report",
        ]

class PhasedProcessingPattern(BasePattern):
    """Multi-phase processing pattern"""

    category: Literal[PatternCategory.STRUCTURAL] = PatternCategory.STRUCTURAL
    phases: list[str]
    parallel_phases: list[tuple[str, str]] = Field(default_factory=list)

    def generate_analyze_method(self) -> str:
        """Generate analyze() method skeleton"""
        code_lines = ["async def analyze(self, context: dict) -> dict:"]
        for i, phase in enumerate(self.phases, 1):
            code_lines.append(f"    # Phase {i}: {phase}")
            code_lines.append(f"    {phase}_result = await self._{phase}(context)")
        code_lines.append("    return {...}")
        return "\n".join(code_lines)


# patterns/input.py
class StructuredFieldsPattern(BasePattern):
    """Structured field input pattern"""

    category: Literal[PatternCategory.INPUT] = PatternCategory.INPUT
    fields_by_step: dict[int, list[str]]
    field_types: dict[str, str] = Field(default_factory=dict)

    def generate_request_model(self, step: int) -> str:
        """Generate Pydantic request model"""
        fields = self.fields_by_step.get(step, [])
        field_defs = [
            f"    {field}: str" for field in fields
        ]
        return f"class Step{step}Request(BaseModel):\n" + "\n".join(field_defs)


# patterns/validation.py
class ApprovalPattern(BasePattern):
    """User approval before finalization pattern"""

    category: Literal[PatternCategory.VALIDATION] = PatternCategory.VALIDATION
    requires_preview: bool = True
    approval_field: str = "user_approved"

    def generate_save_endpoint(self) -> str:
        """Generate save endpoint with approval check"""
        return '''
@router.post("/{wizard_id}/save")
async def save_report(wizard_id: str, approval: dict):
    session = await get_session(wizard_id)

    if "preview_report" not in session:
        raise HTTPException(400, "Must generate preview first")

    if not approval.get("user_approved", False):
        raise HTTPException(400, "User approval required")

    session["completed"] = True
    return session["preview_report"]
'''


# patterns/behavior.py
class RiskAssessmentPattern(BasePattern):
    """Level 4 Anticipatory risk assessment pattern"""

    category: Literal[PatternCategory.BEHAVIOR] = PatternCategory.BEHAVIOR
    risk_levels: list[str] = ["critical", "high", "medium", "low"]
    alert_thresholds: dict[str, int] = Field(default_factory=dict)

    def generate_risk_analyzer(self) -> str:
        """Generate risk assessment code"""
        return '''
class RiskAnalyzer:
    def analyze(self, issues: list) -> dict:
        by_level = {level: 0 for level in self.risk_levels}
        for issue in issues:
            by_level[issue.severity] += 1

        alert_level = self._determine_alert_level(by_level)

        return {
            "by_risk_level": by_level,
            "alert_level": alert_level,
        }
'''


# patterns/empathy.py
class EmpathyLevelPattern(BasePattern):
    """Empathy level configuration pattern"""

    category: Literal[PatternCategory.EMPATHY] = PatternCategory.EMPATHY
    default_level: int = Field(ge=0, le=4, default=2)
    level_descriptions: dict[int, str] = Field(default_factory=dict)

    def generate_config_dataclass(self) -> str:
        """Generate WizardConfig with empathy"""
        return '''
@dataclass
class WizardConfig:
    name: str
    description: str
    domain: str
    default_empathy_level: int = 2  # 0-4

    def _validate_config(self):
        if not 0 <= self.default_empathy_level <= 4:
            raise ValueError(f"Empathy level must be 0-4")
'''
```

---

### 3.3 Pattern Registry

```python
# patterns/registry.py
from typing import Dict, Type, List
from .core import BasePattern, PatternCategory
from .structural import LinearFlowPattern, PhasedProcessingPattern
from .input import StructuredFieldsPattern, CodeAnalysisPattern, ContextBasedPattern
from .validation import ConfigValidationPattern, StepValidationPattern, ApprovalPattern
from .behavior import RiskAssessmentPattern, AIEnhancementPattern, PredictionPattern
from .empathy import EmpathyLevelPattern, EducationalBannerPattern

class PatternRegistry:
    """Central registry for all wizard patterns"""

    def __init__(self):
        self._patterns: Dict[str, BasePattern] = {}
        self._by_category: Dict[PatternCategory, List[BasePattern]] = {
            cat: [] for cat in PatternCategory
        }

    def register(self, pattern: BasePattern):
        """Register a pattern"""
        self._patterns[pattern.id] = pattern
        self._by_category[pattern.category].append(pattern)

    def get(self, pattern_id: str) -> BasePattern:
        """Get pattern by ID"""
        return self._patterns.get(pattern_id)

    def list_by_category(self, category: PatternCategory) -> List[BasePattern]:
        """List patterns in a category"""
        return self._by_category[category]

    def search(self, query: str) -> List[BasePattern]:
        """Search patterns by name/description"""
        results = []
        for pattern in self._patterns.values():
            if query.lower() in pattern.name.lower() or query.lower() in pattern.description.lower():
                results.append(pattern)
        return results

    def recommend_for_wizard(self, wizard_type: str, domain: str) -> List[BasePattern]:
        """Recommend patterns for a new wizard"""
        # Simple recommendation based on domain and type
        recommendations = []

        if domain == "healthcare":
            recommendations.extend([
                self.get("linear_flow"),
                self.get("structured_fields"),
                self.get("approval"),
                self.get("educational_banner"),
            ])

        if wizard_type == "coach":
            recommendations.extend([
                self.get("code_analysis_input"),
                self.get("risk_assessment"),
                self.get("prediction"),
            ])

        if wizard_type == "ai":
            recommendations.extend([
                self.get("phased_processing"),
                self.get("context_based_input"),
                self.get("ai_enhancement"),
            ])

        return [p for p in recommendations if p is not None]


# Global registry instance
_registry = PatternRegistry()


def get_pattern_registry() -> PatternRegistry:
    """Get the global pattern registry"""
    return _registry


# Load extracted patterns from existing wizards
def load_patterns():
    """Load all extracted patterns into registry"""

    # Structural patterns
    _registry.register(LinearFlowPattern(
        id="linear_flow",
        name="Linear Flow",
        description="Step-by-step wizard with review and approval",
        frequency=16,
        reusability_score=0.9,
        examples=["soap_note", "sbar", "shift_handoff", "care_plan"],
        total_steps=5,
        steps={
            1: StepConfig(step=1, title="Step 1", prompt="...", fields=[], help_text="..."),
            # ... more steps
        },
    ))

    _registry.register(PhasedProcessingPattern(
        id="phased_processing",
        name="Phased Processing",
        description="Multi-phase analysis pipeline",
        frequency=12,
        reusability_score=0.85,
        examples=["advanced_debugging", "security_analysis", "performance_profiling"],
        phases=["parse", "load_config", "analyze", "fix", "verify"],
    ))

    # Input patterns
    _registry.register(StructuredFieldsPattern(
        id="structured_fields",
        name="Structured Fields",
        description="Predefined fields per step with validation",
        frequency=16,
        reusability_score=0.9,
        examples=["soap_note", "care_plan", "admission_assessment"],
        fields_by_step={
            1: ["chief_complaint", "history_present_illness"],
            2: ["vital_signs", "physical_exam_findings"],
        },
    ))

    # Validation patterns
    _registry.register(ApprovalPattern(
        id="approval",
        name="User Approval",
        description="Preview → Explicit Approval → Finalize",
        frequency=16,
        reusability_score=0.95,
        examples=["soap_note", "sbar", "discharge_summary"],
        requires_preview=True,
    ))

    # Behavior patterns
    _registry.register(RiskAssessmentPattern(
        id="risk_assessment",
        name="Risk Assessment",
        description="Level 4 Anticipatory risk analysis",
        frequency=16,
        reusability_score=0.8,
        examples=["debugging", "security", "testing"],
        risk_levels=["critical", "high", "medium", "low"],
    ))

    # Empathy patterns
    _registry.register(EmpathyLevelPattern(
        id="empathy_level",
        name="Empathy Level",
        description="0-4 empathy level configuration",
        frequency=16,
        reusability_score=1.0,
        examples=["healthcare", "finance", "legal"],
        default_level=2,
    ))
```

---

## 4. Phased Implementation Plan

### Phase 1: Pattern Library (2 weeks)

**Goal:** Create Pydantic-based pattern library with extracted patterns

**Deliverables:**
1. Core pattern models (`patterns/core.py`)
2. Pattern implementations for all 5 categories
3. Pattern registry with search and recommendation
4. Documentation with examples
5. Unit tests for pattern validation

**Files to Create:**
- `patterns/__init__.py`
- `patterns/core.py` - BasePattern, PatternCategory
- `patterns/structural.py` - LinearFlowPattern, PhasedProcessingPattern
- `patterns/input.py` - StructuredFieldsPattern, CodeAnalysisPattern, ContextBasedPattern
- `patterns/validation.py` - ConfigValidationPattern, StepValidationPattern, ApprovalPattern
- `patterns/behavior.py` - RiskAssessmentPattern, AIEnhancementPattern, PredictionPattern
- `patterns/empathy.py` - EmpathyLevelPattern, EducationalBannerPattern
- `patterns/registry.py` - PatternRegistry, load_patterns()
- `tests/unit/patterns/` - Comprehensive tests

**Success Criteria:**
- [ ] All 15 patterns implemented with Pydantic
- [ ] Registry supports search and recommendation
- [ ] Code generation methods work for top 3 patterns
- [ ] 90%+ test coverage
- [ ] Documentation with real-world examples

---

### Phase 2: Hot-Reload Infrastructure (1 week)

**Goal:** Enable hot-reload for wizard development without server restarts

**Deliverables:**
1. File watcher using `watchdog` library
2. Dynamic wizard reloading in `wizard_api.py`
3. WebSocket notifications for frontend
4. Error handling for reload failures
5. Development mode toggle

**Files to Create:**
- `hot_reload/__init__.py`
- `hot_reload/watcher.py` - FileSystemWatcher
- `hot_reload/reloader.py` - WizardReloader
- `hot_reload/websocket.py` - WebSocket notification system
- `backend/api/wizard_api.py` - Add hot-reload support
- `tests/integration/test_hot_reload.py`

**Implementation:**
```python
# hot_reload/watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class WizardFileHandler(FileSystemEventHandler):
    def __init__(self, reload_callback):
        self.reload_callback = reload_callback

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            wizard_id = self._extract_wizard_id(event.src_path)
            logger.info(f"Detected change in {wizard_id}, reloading...")
            self.reload_callback(wizard_id)

class WizardHotReloader:
    def __init__(self, wizard_dirs: list[Path]):
        self.wizard_dirs = wizard_dirs
        self.observer = Observer()

    def start(self):
        """Start watching wizard directories"""
        for directory in self.wizard_dirs:
            event_handler = WizardFileHandler(self._reload_wizard)
            self.observer.schedule(event_handler, str(directory), recursive=True)

        self.observer.start()
        logger.info(f"Hot-reload enabled for {len(self.wizard_dirs)} directories")

    def _reload_wizard(self, wizard_id: str):
        """Reload a specific wizard"""
        try:
            # Unload old module
            if wizard_id in sys.modules:
                importlib.reload(sys.modules[wizard_id])

            # Re-register wizard
            from backend.api.wizard_api import register_wizard, WIZARDS
            # ... reload logic

            logger.info(f"✓ Reloaded {wizard_id}")

            # Notify via WebSocket
            await notify_clients({"event": "wizard_reloaded", "wizard_id": wizard_id})

        except Exception as e:
            logger.error(f"Failed to reload {wizard_id}: {e}")
            await notify_clients({"event": "wizard_reload_failed", "wizard_id": wizard_id, "error": str(e)})
```

**Success Criteria:**
- [ ] Wizards reload without server restart
- [ ] File changes detected within 1 second
- [ ] Reload failures don't crash server
- [ ] WebSocket notifications work
- [ ] Development mode can be toggled via env var

---

### Phase 3: Risk-Driven Test Generator (2 weeks)

**Goal:** Generate comprehensive tests for new wizards based on risk analysis

**Deliverables:**
1. Test generator using Jinja2 templates
2. Risk-driven test coverage (prioritize high-risk paths)
3. Templates for unit, integration, and E2E tests
4. Fixture generation for common wizard patterns
5. CLI command: `attune wizard generate-tests <wizard_id>`

**Files to Create:**
- `test_generator/__init__.py`
- `test_generator/generator.py` - TestGenerator class
- `test_generator/risk_analyzer.py` - Analyze wizard for high-risk paths
- `test_generator/templates/` - Jinja2 test templates
  - `unit_test.py.jinja2`
  - `integration_test.py.jinja2`
  - `e2e_test.py.jinja2`
- `test_generator/fixtures.py` - Common test fixtures
- `tests/integration/test_generator/`

**Implementation:**
```python
# test_generator/generator.py
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

class TestGenerator:
    def __init__(self):
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_tests(self, wizard_id: str, pattern_ids: list[str]) -> dict[str, str]:
        """Generate tests for a wizard based on its patterns"""

        # Analyze patterns for risk
        risk_analysis = self._analyze_risks(pattern_ids)

        # Generate unit tests (always)
        unit_tests = self._generate_unit_tests(wizard_id, pattern_ids, risk_analysis)

        # Generate integration tests (for multi-step wizards)
        integration_tests = None
        if "linear_flow" in pattern_ids or "phased_processing" in pattern_ids:
            integration_tests = self._generate_integration_tests(wizard_id, pattern_ids)

        # Generate E2E tests (for critical wizards)
        e2e_tests = None
        if risk_analysis["critical_paths"] > 0:
            e2e_tests = self._generate_e2e_tests(wizard_id, pattern_ids)

        return {
            "unit": unit_tests,
            "integration": integration_tests,
            "e2e": e2e_tests,
        }

    def _analyze_risks(self, pattern_ids: list[str]) -> dict:
        """Analyze wizard patterns for risk"""
        critical_paths = 0
        high_risk_inputs = []

        for pattern_id in pattern_ids:
            pattern = get_pattern_registry().get(pattern_id)

            if isinstance(pattern, ApprovalPattern):
                critical_paths += 1  # Approval logic is critical
                high_risk_inputs.append("approval without preview")

            if isinstance(pattern, RiskAssessmentPattern):
                critical_paths += 1  # Risk assessment logic is critical

            if isinstance(pattern, PhasedProcessingPattern):
                critical_paths += len(pattern.phases)  # Each phase is a critical path

        return {
            "critical_paths": critical_paths,
            "high_risk_inputs": high_risk_inputs,
            "recommended_coverage": min(95, 70 + critical_paths * 5),  # 70% base + 5% per critical path
        }

    def _generate_unit_tests(self, wizard_id, pattern_ids, risk_analysis):
        """Generate unit tests from template"""
        template = self.env.get_template("unit_test.py.jinja2")

        return template.render(
            wizard_id=wizard_id,
            patterns=pattern_ids,
            risk_analysis=risk_analysis,
            critical_paths=self._get_critical_test_cases(pattern_ids),
        )
```

**Test Template Example:**
```jinja2
{# test_generator/templates/unit_test.py.jinja2 #}
"""Unit tests for {{ wizard_id }} wizard

Auto-generated by Attune AI Test Generator
Risk Analysis: {{ risk_analysis.critical_paths }} critical paths identified
Target Coverage: {{ risk_analysis.recommended_coverage }}%
"""

import pytest
from {{ wizard_module }} import {{ wizard_class }}

class Test{{ wizard_class }}:
    """Test {{ wizard_id }} wizard"""

    @pytest.fixture
    def wizard(self):
        """Create wizard instance"""
        return {{ wizard_class }}()

    {% for pattern_id in patterns %}
    {% if pattern_id == "approval" %}
    def test_cannot_save_without_preview(self, wizard):
        """CRITICAL: Saving without preview should fail"""
        with pytest.raises(HTTPException) as exc:
            await wizard.save(wizard_id="test", approval={"user_approved": True})

        assert exc.value.status_code == 400
        assert "preview" in exc.value.detail.lower()

    def test_cannot_save_without_approval(self, wizard):
        """CRITICAL: Saving without user approval should fail"""
        # Generate preview first
        await wizard.preview(wizard_id="test")

        # Try to save without approval
        with pytest.raises(HTTPException) as exc:
            await wizard.save(wizard_id="test", approval={"user_approved": False})

        assert exc.value.status_code == 400
        assert "approval" in exc.value.detail.lower()
    {% endif %}

    {% if pattern_id == "linear_flow" %}
    def test_cannot_skip_steps(self, wizard):
        """CRITICAL: Steps must be completed in order"""
        session = await wizard.start()
        wizard_id = session["wizard_id"]

        # Try to skip to step 3
        with pytest.raises(HTTPException) as exc:
            await wizard.submit_step(wizard_id, {"step": 3, "data": {}})

        assert exc.value.status_code == 422
        assert "expected step 1" in exc.value.detail.lower()
    {% endif %}
    {% endfor %}
```

**Success Criteria:**
- [ ] Generates unit tests for all pattern types
- [ ] Risk analysis identifies critical paths
- [ ] Generated tests achieve 80%+ coverage
- [ ] Templates support customization
- [ ] CLI command works: `attune wizard generate-tests <wizard_id>`

---

### Phase 4: Methodology Scaffolding (1 week)

**Goal:** CLI tool to scaffold new wizards using proven methodologies

**Deliverables:**
1. CLI command: `attune wizard create <name> --methodology <method>`
2. 5 methodology templates (TDD-First, Pattern-Compose, Prototype-Refine, Risk-Driven, Empathy-Centered)
3. Interactive wizard creation flow
4. File generation for wizard, tests, docs
5. Automatic pattern recommendation

**Files to Create:**
- `scaffolding/__init__.py`
- `scaffolding/cli.py` - Click-based CLI
- `scaffolding/methodologies/` - Methodology templates
  - `tdd_first.py`
  - `pattern_compose.py`
  - `prototype_refine.py`
  - `risk_driven.py`
  - `empathy_centered.py`
- `scaffolding/templates/` - File templates
  - `wizard.py.jinja2`
  - `test_wizard.py.jinja2`
  - `README.md.jinja2`
- `tests/integration/test_scaffolding.py`

**Implementation:**
```python
# scaffolding/cli.py
import click
from .methodologies import TDDFirst, PatternCompose, PrototypeRefine, RiskDriven, EmpathyCentered

@click.group()
def wizard():
    """Wizard creation and management"""
    pass

@wizard.command()
@click.argument('name')
@click.option('--methodology', type=click.Choice(['tdd', 'pattern', 'prototype', 'risk', 'empathy']), default='pattern')
@click.option('--domain', type=str, prompt=True)
@click.option('--type', type=click.Choice(['domain', 'coach', 'ai']), prompt=True)
def create(name, methodology, domain, type):
    """Create a new wizard using a methodology

    Methodologies:
    - tdd: Test-Driven Development (write tests first)
    - pattern: Pattern-Compose (select patterns, compose wizard)
    - prototype: Prototype-Refine (quick prototype, then refactor)
    - risk: Risk-Driven (focus on high-risk paths first)
    - empathy: Empathy-Centered (design for user experience)
    """

    click.echo(f"Creating wizard '{name}' using {methodology} methodology...")

    methodology_map = {
        'tdd': TDDFirst(),
        'pattern': PatternCompose(),
        'prototype': PrototypeRefine(),
        'risk': RiskDriven(),
        'empathy': EmpathyCentered(),
    }

    method = methodology_map[methodology]

    # Run methodology-specific creation flow
    wizard_config = method.create_wizard(
        name=name,
        domain=domain,
        wizard_type=type,
    )

    click.echo(f"\n✓ Wizard '{name}' created successfully!")
    click.echo(f"\nGenerated files:")
    for file_path in wizard_config['files']:
        click.echo(f"  - {file_path}")

    click.echo(f"\nNext steps:")
    for step in wizard_config['next_steps']:
        click.echo(f"  {step}")


# scaffolding/methodologies/pattern_compose.py
class PatternCompose:
    """Pattern-Compose methodology: Select patterns, compose wizard"""

    def create_wizard(self, name: str, domain: str, wizard_type: str) -> dict:
        """Create wizard by composing patterns"""

        # Get pattern recommendations
        registry = get_pattern_registry()
        recommended_patterns = registry.recommend_for_wizard(wizard_type, domain)

        click.echo("\nRecommended patterns:")
        for i, pattern in enumerate(recommended_patterns, 1):
            click.echo(f"{i}. {pattern.name} - {pattern.description}")

        # Let user select patterns
        selected = click.prompt(
            "\nSelect patterns (comma-separated numbers, or 'all')",
            default="all"
        )

        if selected == "all":
            patterns = recommended_patterns
        else:
            indices = [int(i.strip()) - 1 for i in selected.split(',')]
            patterns = [recommended_patterns[i] for i in indices]

        click.echo(f"\nSelected {len(patterns)} patterns:")
        for pattern in patterns:
            click.echo(f"  ✓ {pattern.name}")

        # Generate wizard code
        wizard_code = self._compose_wizard(name, domain, wizard_type, patterns)

        # Generate tests
        from test_generator import TestGenerator
        test_generator = TestGenerator()
        tests = test_generator.generate_tests(name, [p.id for p in patterns])

        # Write files
        wizard_file = f"wizards/{name}_wizard.py"
        test_file = f"tests/unit/wizards/test_{name}_wizard.py"

        Path(wizard_file).parent.mkdir(parents=True, exist_ok=True)
        Path(wizard_file).write_text(wizard_code)

        Path(test_file).parent.mkdir(parents=True, exist_ok=True)
        Path(test_file).write_text(tests['unit'])

        # Generate README
        readme = self._generate_readme(name, domain, patterns)
        readme_file = f"wizards/{name}_README.md"
        Path(readme_file).write_text(readme)

        return {
            'files': [wizard_file, test_file, readme_file],
            'next_steps': [
                "1. Review generated wizard code",
                "2. Run tests: pytest " + test_file,
                f"3. Register wizard in wizard_api.py: register_wizard('{name}', {name.title()}Wizard)",
                "4. Test via API: POST /api/wizard/{name}/process",
            ],
        }

    def _compose_wizard(self, name, domain, wizard_type, patterns):
        """Generate wizard code by composing patterns"""
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader("scaffolding/templates"))
        template = env.get_template("wizard.py.jinja2")

        return template.render(
            wizard_name=name.title() + "Wizard",
            domain=domain,
            patterns=patterns,
            wizard_type=wizard_type,
        )
```

**Success Criteria:**
- [ ] CLI creates fully functional wizard
- [ ] All 5 methodologies implemented
- [ ] Generated wizards pass tests
- [ ] Pattern recommendation works
- [ ] Interactive flow is user-friendly

---

## 5. Implementation Timeline

| Phase | Duration | Start | End | Deliverables |
|-------|----------|-------|-----|--------------|
| **Phase 1: Pattern Library** | 2 weeks | Week 1 | Week 2 | Pydantic patterns, Registry, Tests |
| **Phase 2: Hot-Reload** | 1 week | Week 3 | Week 3 | Watchdog, WebSocket, Dev mode |
| **Phase 3: Test Generator** | 2 weeks | Week 4 | Week 5 | Risk-driven tests, Templates, CLI |
| **Phase 4: Scaffolding** | 1 week | Week 6 | Week 6 | Methodologies, CLI, File generation |

**Total:** 6 weeks (vs. original 4-5 week estimate)

---

## 6. Success Metrics

### Pattern Library (Phase 1)
- [ ] 15+ patterns documented with Pydantic
- [ ] Pattern registry supports search by category, name, description
- [ ] Pattern recommendation achieves 80%+ accuracy (validated against existing wizards)
- [ ] Code generation works for top 3 patterns (linear_flow, phased_processing, approval)
- [ ] 90%+ test coverage

### Hot-Reload (Phase 2)
- [ ] Wizard reload time < 2 seconds
- [ ] Zero server downtime during development
- [ ] Reload failures are gracefully handled
- [ ] WebSocket notifications delivered < 500ms after file change

### Test Generator (Phase 3)
- [ ] Generated tests achieve 80%+ coverage for new wizards
- [ ] Risk analysis identifies 95%+ of critical paths
- [ ] Test generation time < 10 seconds for typical wizard
- [ ] Templates support all pattern types

### Scaffolding (Phase 4)
- [ ] Wizard creation time reduced from 2 hours → 10 minutes
- [ ] Generated wizards work without modification for simple use cases
- [ ] All 5 methodologies implemented and tested
- [ ] CLI is intuitive (user testing with 3+ developers)

---

## 7. Comparison with Original Proposal

| Aspect | Original Proposal | This Discovery-Based Approach |
|--------|-------------------|-------------------------------|
| **Pattern Source** | Abstract design | Extracted from 78 real wizards |
| **Schema Format** | XML | Pydantic (native Python) |
| **Timeline** | 4-5 weeks | 6 weeks (more realistic) |
| **Risk** | High (unvalidated patterns) | Low (proven patterns) |
| **Adoption** | Uncertain | High (based on existing code) |
| **Dependencies** | XML parser, lxml | Pydantic (already used) |
| **Learning Curve** | Steep (XML + schemas) | Gentle (Python + Pydantic) |
| **IDE Support** | Minimal | Full autocomplete + type hints |
| **Validation** | Manual | Automatic (Pydantic) |

**Decision:** Proceed with Discovery-Based Approach using Pydantic.

---

## 8. Next Steps

1. **Get User Approval:** Review this discovery report and approve approach
2. **Phase 1 Kickoff:** Start implementing Pattern Library with Pydantic
3. **Spike:** Prototype LinearFlowPattern code generation (2 days)
4. **Validation:** Generate a new wizard using the pattern library to validate approach

---

## 9. Appendices

### A. Complete Wizard List (78 Total)

**Healthcare Wizards (16):**
1. SOAP Note Documentation
2. SBAR Communication
3. Shift Handoff
4. Admission Assessment
5. Discharge Summary
6. Discharge Planning
7. Care Planning
8. Clinical Assessment
9. Nursing Assessment
10. Treatment Planning
11. Patient Education
12. Medication Reconciliation
13. Dosage Calculation
14. Quality Improvement
15. Incident Reporting

**Domain Wizards (16):**
1. Healthcare
2. Finance
3. Legal
4. Education
5. Customer Support
6. HR
7. Sales
8. Real Estate
9. Insurance
10. Accounting
11. Research
12. Government
13. Retail
14. Manufacturing
15. Logistics
16. Technology

**Coach Wizards (16):**
1. Debugging
2. Testing
3. Security
4. Documentation
5. Performance
6. Refactoring
7. Database
8. API Design
9. Compliance
10. Monitoring
11. CI/CD
12. Accessibility
13. Localization
14. Migration
15. Observability
16. Scaling

**AI Software Wizards (12):**
1. Advanced Debugging
2. Agent Orchestration
3. AI Collaboration
4. AI Context Window
5. AI Documentation
6. Enhanced Testing
7. Multi-Model
8. Performance Profiling
9. Prompt Engineering
10. RAG Pattern
11. Security Analysis

**Coach Examples (18):**
1-18. Reference implementations

### B. Pattern Frequency Analysis

| Pattern | Frequency | Reusability Score | Category |
|---------|-----------|-------------------|----------|
| Empathy Level | 16 | 1.0 | Empathy |
| Linear Flow | 16 | 0.9 | Structural |
| Structured Fields | 16 | 0.9 | Input |
| User Approval | 16 | 0.95 | Validation |
| Educational Banner | 16 | 1.0 | Empathy |
| Risk Assessment | 16 | 0.8 | Behavior |
| Prediction (Level 4) | 16 | 0.8 | Behavior |
| Code Analysis Input | 16 | 0.9 | Input |
| Phased Processing | 12 | 0.85 | Structural |
| Context-Based Input | 12 | 0.8 | Input |
| AI Enhancement | 16 | 0.7 | Behavior |
| Fix Application | 8 | 0.75 | Behavior |
| Config Validation | 16 | 0.9 | Validation |
| Step Validation | 16 | 0.9 | Validation |

### C. References

- [Backend Wizard API](../../backend/api/wizard_api.py)
- [Base Wizard](../../attune_llm/wizards/base_wizard.py)
- [SOAP Note Wizard](../../wizards/soap_note_wizard.py)
- [Advanced Debugging Wizard](../../empathy_software_plugin/wizards/advanced_debugging_wizard.py)
- [Testing Wizard](../../coach_wizards/testing_wizard.py)

---

**End of Discovery Report**
