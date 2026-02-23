# Wizard Scaffolding System

**Fast, pattern-based wizard creation for Attune AI**

Generate production-ready wizards in 10 minutes instead of 2 hours using proven patterns extracted from 78 existing wizards.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Methodologies](#methodologies)
- [Commands](#commands)
- [Patterns](#patterns)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Create Your First Wizard

```bash
# Recommended: Pattern-Compose methodology
python -m scaffolding create patient_intake --domain healthcare

# This generates:
# - attune_llm/wizards/patient_intake_wizard.py (production-ready)
# - tests/unit/wizards/test_patient_intake_wizard.py (comprehensive tests)
# - tests/unit/wizards/fixtures_patient_intake.py (test fixtures)
# - attune_llm/wizards/patient_intake_README.md (documentation)
```

### View Available Patterns

```bash
python -m scaffolding list-patterns

# Output:
# STRUCTURAL (3 patterns):
#   - linear_flow             | Linear Flow          | Reusability: 0.92
#   - phased_processing       | Phased Processing    | Reusability: 0.82
#   - session_based           | Session Based        | Reusability: 0.95
# ...
```

### Interactive Mode

```bash
python -m scaffolding create my_wizard --interactive --domain finance

# Prompts:
# Select patterns (comma-separated numbers, or 'all' for all):
# 1. Linear Flow - Step-by-step linear wizard flow
# 2. Structured Fields - Strongly typed field validation
# 3. Approval Pattern - Preview before finalize workflow
# 4. Educational Banner - Level-based user guidance
# >
```

---

## Methodologies

### Pattern-Compose (RECOMMENDED)

**Best for:** Most wizards (95% of use cases)

**Workflow:**
1. Recommends patterns based on domain and type
2. User selects patterns (or uses all recommended)
3. Generates complete wizard from patterns
4. Generates comprehensive tests automatically
5. Generates documentation

**Pros:**
- ✅ Fast (10 minutes)
- ✅ Leverages proven patterns (from 78 existing wizards)
- ✅ Automatic test generation
- ✅ High quality, consistent code
- ✅ Great for newcomers

**Example:**
```bash
python -m scaffolding create soap_note --domain healthcare --methodology pattern

# Generated files:
# - attune_llm/wizards/soap_note_wizard.py
# - tests/unit/wizards/test_soap_note_wizard.py (with risk-based priorities)
# - tests/unit/wizards/fixtures_soap_note.py
# - attune_llm/wizards/soap_note_README.md
```

---

## Commands

### `create` - Create a New Wizard

```bash
python -m scaffolding create <name> [OPTIONS]
```

**Required Arguments:**
- `<name>` - Wizard name (snake_case, e.g., `patient_intake`)

**Options:**
- `--domain, -d` - Domain (e.g., healthcare, finance, legal)
- `--type, -t` - Wizard type (choices: domain, coach, ai; default: domain)
- `--methodology, -m` - Methodology (choices: pattern; default: pattern)
- `--patterns, -p` - Comma-separated pattern IDs (manual selection)
- `--interactive, -i` - Interactive pattern selection

**Examples:**

```bash
# Basic usage (recommended patterns automatically selected)
python -m scaffolding create patient_intake --domain healthcare

# Interactive pattern selection
python -m scaffolding create my_wizard --interactive --domain legal

# Manual pattern selection
python -m scaffolding create my_wizard --patterns linear_flow,approval,structured_fields

# Coach wizard type
python -m scaffolding create debugging --domain software --type coach

# AI wizard type
python -m scaffolding create code_fix --domain software --type ai
```

### `list-patterns` - View Available Patterns

```bash
python -m scaffolding list-patterns
```

**Output:**
- Patterns grouped by category (structural, input, validation, behavior, empathy)
- Pattern ID, name, and reusability score
- Total patterns and average reusability

---

## Patterns

### Pattern Categories

| Category | Description | Example Patterns |
|----------|-------------|------------------|
| **Structural** | Wizard flow and architecture | linear_flow, phased_processing |
| **Input** | How wizards receive data | structured_fields, code_analysis_input |
| **Validation** | Data validation approaches | step_validation, approval |
| **Behavior** | Wizard capabilities | risk_assessment, prediction, fix_application |
| **Empathy** | User experience enhancements | empathy_level, educational_banner, user_guidance |

### Recommended Patterns by Domain

#### Healthcare Wizards
- `linear_flow` - Step-by-step workflow
- `structured_fields` - HIPAA-compliant field validation
- `approval` - Preview before finalize (critical for medical notes)
- `educational_banner` - Level 2+ empathy for guidance

#### Coach Wizards (Software Development)
- `code_analysis_input` - Parse and analyze code
- `risk_assessment` - Identify code risks
- `prediction` - Predict future issues
- `fix_application` - Suggest and apply fixes

#### AI Wizards
- `phased_processing` - Multi-phase execution
- `context_based_input` - Rich context handling
- `ai_enhancement` - LLM-powered capabilities

#### Finance Wizards
- `approval` - Required for financial transactions
- `risk_assessment` - Financial risk analysis
- `step_validation` - Strict step sequencing

### Pattern Details

Run `python -m scaffolding list-patterns` to see:
- All 15 patterns
- Descriptions
- Reusability scores (0.0-1.0)
- Which wizards use each pattern

---

## Examples

### Example 1: Healthcare SOAP Note Wizard

```bash
python -m scaffolding create soap_note --domain healthcare

# Generated wizard includes:
# - 5-step linear flow (Subjective, Objective, Assessment, Plan, Review)
# - Structured fields with validation
# - Preview before save (approval pattern)
# - Educational banners (Level 2 empathy)
# - Comprehensive tests (90%+ coverage recommended)
```

**Generated Code Structure:**
```python
# soap_note_wizard.py
@router.post("/start")
async def start_wizard(request: StartRequest) -> StartResponse:
    # Initialize wizard session
    # Returns wizard_id, current_step, total_steps, educational_banner

@router.post("/{wizard_id}/step")
async def submit_step(wizard_id: str, submission: StepSubmission) -> StepResult:
    # Submit step data with validation
    # Returns next_step_guidance (Level 2 empathy)

@router.post("/{wizard_id}/preview")
async def generate_preview(wizard_id: str) -> PreviewResult:
    # Generate preview for user review (approval pattern)

@router.post("/{wizard_id}/save")
async def save_with_approval(wizard_id: str, request: SaveRequest) -> SaveResult:
    # Save with user approval
```

### Example 2: Debugging Coach Wizard

```bash
python -m scaffolding create debugging --domain software --type coach

# Generated wizard includes:
# - Code analysis endpoint
# - Risk assessment
# - Prediction of future issues
# - Fix suggestions
# - Fix application with approval
```

**Generated Code Structure:**
```python
# debugging_wizard.py
@router.post("/analyze")
async def analyze_code(request: AnalysisRequest) -> AnalysisResult:
    # Analyze code
    # Returns analysis, risk_assessment, predictions, suggested_fixes

@router.post("/fix/apply")
async def apply_fix(request: FixRequest) -> FixResult:
    # Apply fix with user approval
    # Returns modified_code
```

---

## Advanced Usage

### Custom Output Directory

```python
from scaffolding.methodologies.pattern_compose import PatternCompose
from pathlib import Path

method = PatternCompose()
result = method.create_wizard(
    name="custom_wizard",
    domain="custom",
    wizard_type="domain",
    output_dir=Path("custom/wizards"),
)

print(f"Generated files: {result['files']}")
print(f"Patterns used: {result['patterns']}")
print(f"Next steps: {result['next_steps']}")
```

### Programmatic Pattern Selection

```python
from patterns import get_pattern_registry

registry = get_pattern_registry()

# Get recommendations
recommended = registry.recommend_for_wizard(
    wizard_type="domain",
    domain="healthcare",
)

# Filter patterns
selected = [p.id for p in recommended if p.reusability_score > 0.8]

# Create wizard with selected patterns
method = PatternCompose()
result = method.create_wizard(
    name="my_wizard",
    domain="healthcare",
    wizard_type="domain",
    selected_patterns=selected,
)
```

### Integration with Wizard API

After generating a wizard, register it with the Wizard API:

```python
# backend/api/wizard_api.py
from wizards.soap_note_wizard import router as soap_note_router

# Register router
app.include_router(soap_note_router, prefix="/api/wizard")

# Register wizard class (for hot-reload)
from wizards.soap_note_wizard import SOAPNoteWizard
register_wizard("soap_note", SOAPNoteWizard)
```

### Hot-Reload Integration

Generated wizards work seamlessly with hot-reload:

```python
# Enable hot-reload
export HOT_RELOAD_ENABLED=true
export HOT_RELOAD_WATCH_DIRS="wizards,coach_wizards,attune_llm/wizards"

# Start server
uvicorn backend.main:app --reload

# Edit generated wizard - server auto-reloads!
# vim wizards/soap_note_wizard.py
```

---

## Troubleshooting

### Issue: Generated wizard has import errors

**Cause:** Module paths differ based on wizard type

**Solution:**
- Domain wizards → `attune_llm/wizards/`
- Coach wizards → `coach_wizards/`
- AI wizards → `wizards/`

Verify wizard was generated in correct directory based on `--type` flag.

### Issue: Tests fail after generation

**Cause:** Generated tests are placeholders for custom logic

**Solution:**
1. Review generated tests
2. Implement custom logic in wizard
3. Update test expectations
4. Run: `pytest tests/unit/wizards/test_<name>_wizard.py`

### Issue: Pattern not found

**Cause:** Invalid pattern ID in `--patterns` flag

**Solution:**
Run `python -m scaffolding list-patterns` to see valid pattern IDs.

### Issue: Template rendering error

**Cause:** Missing context variables for template

**Solution:**
File a bug with:
```bash
python -m scaffolding create <name> --domain <domain> --type <type> 2>&1 | tee error.log
```

### Issue: Permission denied creating files

**Cause:** Output directory doesn't exist or lacks write permissions

**Solution:**
```bash
# Create output directory
mkdir -p wizards coach_wizards attune_llm/wizards tests/unit/wizards

# Fix permissions
chmod -R u+w wizards coach_wizards attune_llm/wizards tests/unit/wizards
```

---

## Architecture

### How It Works

1. **Pattern Registry** - 15 pre-loaded patterns from 78 existing wizards
2. **Pattern Recommendation** - AI-powered pattern selection based on domain/type
3. **Template Selection** - Choose template based on wizard type and patterns
4. **Code Generation** - Jinja2 rendering with pattern-specific logic
5. **Test Generation** - Risk-based test prioritization via TestGenerator
6. **Documentation** - Auto-generated README with usage examples

### Directory Structure

```
scaffolding/
├── __init__.py              # Package exports
├── __main__.py              # Module entry point
├── cli.py                   # CLI commands (create, list-patterns)
├── README.md                # This file
├── methodologies/
│   ├── __init__.py
│   └── pattern_compose.py   # Pattern-Compose methodology (RECOMMENDED)
└── templates/
    ├── linear_flow_wizard.py.jinja2  # Linear flow template
    ├── coach_wizard.py.jinja2        # Coach wizard template
    ├── domain_wizard.py.jinja2       # Domain wizard template
    └── base_wizard.py.jinja2         # Generic fallback
```

### Integration Points

- **patterns/** - Pattern library and registry
- **test_generator/** - Risk-driven test generation
- **hot_reload/** - Hot-reload infrastructure for development
- **backend/api/wizard_api.py** - Wizard registration

---

## Next Steps

1. **Create your first wizard:**
   ```bash
   python -m scaffolding create my_wizard --domain healthcare --interactive
   ```

2. **Review generated code:**
   - Wizard implementation
   - Generated tests
   - README documentation

3. **Register with API:**
   - Add to `backend/api/wizard_api.py`
   - Test via API: `POST /api/wizard/my_wizard/start`

4. **Enable hot-reload:**
   ```bash
   export HOT_RELOAD_ENABLED=true
   uvicorn backend.main:app --reload
   ```

5. **Iterate and customize:**
   - Edit generated wizard
   - Add domain-specific logic
   - Run tests: `pytest tests/unit/wizards/test_my_wizard_wizard.py`

---

## Contributing

### Adding New Patterns

1. Define pattern in `patterns/<category>.py`
2. Register in `patterns/registry.py`
3. Add pattern detection logic
4. Update recommendation algorithm
5. Add tests

### Adding New Templates

1. Create template in `scaffolding/templates/`
2. Update `PatternCompose._get_template_name()`
3. Add template context variables
4. Test with various pattern combinations

### Improving Methodologies

1. Create new methodology in `scaffolding/methodologies/`
2. Implement `create_wizard()` method
3. Add CLI integration in `scaffolding/cli.py`
4. Document in this README

---

## Performance

- **Pattern-Compose:** ~10 minutes (12x faster than manual)
- **Manual wizard creation:** ~2 hours

---

## FAQ

**Q: Which methodology should I use?**
A: Pattern-Compose for 95% of wizards. It leverages proven patterns from 78 existing wizards.

**Q: Can I modify generated code?**
A: Absolutely! Generated code is a starting point. Customize as needed.

**Q: How do I add custom patterns?**
A: See [Contributing](#contributing) → Adding New Patterns

**Q: Can I use multiple patterns?**
A: Yes! Most wizards use 3-5 patterns. Use `--interactive` to select.

**Q: How do I test generated wizards?**
A: Run `pytest tests/unit/wizards/test_<name>_wizard.py`

**Q: What's the difference between wizard types?**
A: Domain (business logic), Coach (code analysis), AI (LLM-powered)

---

## License

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0

---

**Generated by:** Attune AI - Wizard Factory
**Version:** 1.8.0-alpha
**Last Updated:** 2025-01-05
