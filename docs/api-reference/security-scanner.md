---
description: Security Scanner API Reference API reference: **Version:** 1.0 **Module:** `attune.workflows.security_audit` and `attune.workflows.securit
---

# Security Scanner API Reference

**Version:** 1.0
**Module:** `attune.workflows.security_audit` and `attune.workflows.security_audit_phase3`
**Last Updated:** 2026-01-26

---

## Overview

This document provides comprehensive API documentation for the Attune AI Security Scanner. It covers all public classes, functions, and usage patterns for running security audits and extending the scanner.

---

## Table of Contents

1. [Workflow API](#workflow-api)
2. [Phase 3 AST Module](#phase-3-ast-module)
3. [Configuration](#configuration)
4. [Return Types](#return-types)
5. [Usage Examples](#usage-examples)
6. [Extension Guide](#extension-guide)

---

## Workflow API

### SecurityAuditWorkflow

Main workflow class for running security audits.

**Import:**
```python
from attune.workflows.security_audit import SecurityAuditWorkflow
```

#### Constructor

```python
def __init__(self) -> None:
    """Initialize security audit workflow."""
```

**Example:**
```python
workflow = SecurityAuditWorkflow()
```

---

#### run()

Execute a security audit on specified path.

```python
def run(self, input_data: dict) -> dict:
    """Execute security audit workflow.

    Args:
        input_data: Configuration dictionary with keys:
            - path (str, optional): Directory or file to scan. Defaults to "."
            - include (list[str], optional): File patterns to include (e.g., ["*.py"])
            - exclude (list[str], optional): Patterns to exclude (e.g., ["test_*"])
            - json_output (bool, optional): Return JSON-serializable dict. Defaults to False

    Returns:
        dict: Audit results with structure:
            {
                "score": int,  # Security score 0-100
                "findings": list[dict],  # List of security findings
                "summary": {
                    "total": int,
                    "by_severity": {
                        "critical": int,
                        "medium": int,
                        "low": int
                    },
                    "by_type": {
                        "sql_injection": int,
                        "command_injection": int,
                        "insecure_random": int,
                        ...
                    }
                },
                "metadata": {
                    "scan_time": float,
                    "files_scanned": int,
                    "scanner_version": str
                }
            }

    Raises:
        ValueError: If path does not exist
        PermissionError: If insufficient permissions to read files

    Example:
        >>> workflow = SecurityAuditWorkflow()
        >>> results = workflow.run({"path": "./src", "exclude": ["test_*"]})
        >>> print(f"Score: {results['score']}/100")
        >>> print(f"Found {results['summary']['total']} issues")
    """
```

**Usage Examples:**

```python
# Scan entire project
results = workflow.run({"path": "."})

# Scan specific directory
results = workflow.run({"path": "./src/api"})

# Scan with exclusions
results = workflow.run({
    "path": ".",
    "exclude": ["test_*", ".venv/*", "node_modules/*"]
})

# JSON output (for CI/CD)
results = workflow.run({"path": ".", "json_output": True})
```

---

### Finding Dictionary Structure

Each finding in the `findings` list has this structure:

```python
{
    "type": str,           # Vulnerability type: "sql_injection", "command_injection", etc.
    "severity": str,       # "critical", "medium", or "low"
    "file": str,           # Relative path to file
    "line": int,           # Line number (1-indexed)
    "match": str,          # Text that matched the pattern
    "context": str,        # Surrounding code (3 lines)
    "owasp": str,          # OWASP category (e.g., "A03:2021 Injection")
    "description": str,    # Human-readable description
    "recommendation": str, # How to fix the issue
}
```

**Example Finding:**

```python
{
    "type": "command_injection",
    "severity": "critical",
    "file": "src/api/eval_endpoint.py",
    "line": 42,
    "match": "eval(user_input)",
    "context": "def process_formula(formula):\n    result = eval(user_input)  # Dangerous!\n    return result",
    "owasp": "A03:2021 Injection",
    "description": "Use of eval() on untrusted input allows arbitrary code execution",
    "recommendation": "Use ast.literal_eval() for safe literal evaluation, or json.loads() for structured data"
}
```

---

## Phase 3 AST Module

Advanced AST-based detection functions for command injection.

**Import:**
```python
from attune.workflows.security_audit_phase3 import (
    EvalExecDetector,
    analyze_file_for_eval_exec,
    is_scanner_implementation_file,
    enhanced_command_injection_detection,
    apply_phase3_filtering,
)
```

---

### EvalExecDetector

AST visitor class for detecting eval/exec calls.

```python
class EvalExecDetector(ast.NodeVisitor):
    """AST visitor that detects actual eval() and exec() calls.

    Attributes:
        file_path (str): Path to file being analyzed
        findings (list[dict]): Detected eval/exec calls
    """

    def __init__(self, file_path: str):
        """Initialize detector.

        Args:
            file_path: Path to Python file being analyzed
        """

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call nodes to detect eval/exec.

        Args:
            node: AST Call node
        """
```

**Usage:**

```python
import ast
from attune.workflows.security_audit_phase3 import EvalExecDetector

# Parse Python file
with open("src/api/users.py") as f:
    code = f.read()
    tree = ast.parse(code)

# Detect eval/exec calls
detector = EvalExecDetector("src/api/users.py")
detector.visit(tree)

# Access findings
for finding in detector.findings:
    print(f"Found {finding['function']} at line {finding['line']}")
```

---

### analyze_file_for_eval_exec()

Analyze a Python file for actual eval/exec usage using AST.

```python
def analyze_file_for_eval_exec(file_path: str | Path) -> list[dict[str, Any]]:
    """Analyze a Python file for actual eval/exec usage using AST.

    This function parses the Python file into an AST and detects actual
    function calls to eval() or exec(). String mentions in comments,
    docstrings, or literals are ignored.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        List of findings with structure:
            [
                {
                    "type": "command_injection",
                    "function": str,  # "eval" or "exec"
                    "line": int,      # Line number
                    "col": int,       # Column offset
                    "file": str,      # File path
                },
                ...
            ]
        Returns empty list if:
        - File does not exist
        - File has syntax errors (cannot parse)
        - No eval/exec calls found

    Example:
        >>> from attune.workflows.security_audit_phase3 import analyze_file_for_eval_exec
        >>> findings = analyze_file_for_eval_exec("src/api/auth.py")
        >>> if findings:
        ...     print(f"Found {len(findings)} eval/exec calls")
        ...     for f in findings:
        ...         print(f"  Line {f['line']}: {f['function']}()")
        ... else:
        ...     print("No eval/exec calls found")
    """
```

**Usage Examples:**

```python
# Analyze single file
findings = analyze_file_for_eval_exec("src/api/users.py")

# Analyze multiple files
from pathlib import Path

all_findings = []
for py_file in Path("src").rglob("*.py"):
    findings = analyze_file_for_eval_exec(py_file)
    all_findings.extend(findings)

print(f"Total eval/exec calls: {len(all_findings)}")
```

---

### is_scanner_implementation_file()

Check if a file is part of security scanner implementation.

```python
def is_scanner_implementation_file(file_path: str) -> bool:
    """Check if file is part of security scanner implementation.

    Scanner implementation files legitimately contain vulnerability
    patterns for detection purposes. These files should be excluded
    from security audits to avoid false positives.

    Detection criteria:
    - File name contains: bug_predict, security_audit, security_scan,
      vulnerability_scan, owasp, secrets_detector
    - Test files for scanner: test_bug_predict*, test_scanner*

    Args:
        file_path: File path to check (absolute or relative)

    Returns:
        True if file is scanner implementation, False otherwise

    Example:
        >>> is_scanner_implementation_file("src/workflows/security_audit.py")
        True
        >>> is_scanner_implementation_file("src/api/users.py")
        False
        >>> is_scanner_implementation_file("tests/test_bug_predict_helpers.py")
        True
    """
```

**Usage:**

```python
# Check individual files
if is_scanner_implementation_file("src/workflows/bug_predict.py"):
    print("This is a scanner file, skip analysis")

# Filter file list
files_to_scan = [
    f for f in all_files
    if not is_scanner_implementation_file(str(f))
]
```

---

### enhanced_command_injection_detection()

Apply AST-based filtering to command injection findings.

```python
def enhanced_command_injection_detection(
    file_path: str,
    findings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply AST-based filtering to command injection findings.

    This function takes regex-detected command injection findings and
    filters out false positives using AST analysis.

    Process:
    1. Check if file is scanner implementation (auto-exclude all)
    2. For Python files: Use AST to find actual eval/exec calls
    3. Compare AST findings with regex findings
    4. Only keep findings confirmed by both methods
    5. For non-Python files: Use context-based filtering

    Args:
        file_path: Path to file being analyzed
        findings: List of regex-detected command injection findings
                 (should only contain command_injection type)

    Returns:
        Filtered list of findings (false positives removed)

    Example:
        >>> # Regex detected 5 eval mentions
        >>> regex_findings = [
        ...     {"file": "scanner.py", "line": 50, "match": "eval("},  # False positive
        ...     {"file": "app.py", "line": 100, "match": "eval("},     # Actual call
        ...     # ... more findings
        ... ]
        >>>
        >>> # Apply AST filtering
        >>> filtered = enhanced_command_injection_detection("app.py", regex_findings)
        >>> print(f"Filtered {len(regex_findings) - len(filtered)} false positives")
    """
```

**Usage:**

```python
# After regex-based detection
regex_findings = scan_with_regex(file_path)

# Apply AST-based filtering
cmd_findings = [f for f in regex_findings if f["type"] == "command_injection"]
filtered = enhanced_command_injection_detection(file_path, cmd_findings)

print(f"Before: {len(cmd_findings)} findings")
print(f"After: {len(filtered)} findings")
print(f"Filtered: {len(cmd_findings) - len(filtered)} false positives")
```

---

### apply_phase3_filtering()

Main entry point for Phase 3 filtering pipeline.

```python
def apply_phase3_filtering(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply Phase 3 AST-based filtering to command injection findings.

    This is the main entry point for Phase 3 improvements. It groups
    findings by file and applies enhanced detection to each file.

    Args:
        findings: List of command injection findings from regex-based detection
                 (should only contain command_injection type)

    Returns:
        Filtered list with false positives removed

    Example:
        >>> from attune.workflows.security_audit_phase3 import apply_phase3_filtering
        >>>
        >>> # Findings from Phase 1 regex detection
        >>> phase1_findings = [
        ...     {"type": "command_injection", "file": "src/api.py", "line": 42, ...},
        ...     {"type": "command_injection", "file": "src/scanner.py", "line": 100, ...},
        ...     # ... more findings
        ... ]
        >>>
        >>> # Apply Phase 3 filtering
        >>> phase3_findings = apply_phase3_filtering(phase1_findings)
        >>>
        >>> print(f"Phase 1: {len(phase1_findings)} findings")
        >>> print(f"Phase 3: {len(phase3_findings)} findings")
        >>> print(f"Filtered: {len(phase1_findings) - len(phase3_findings)} false positives")
    """
```

**Usage:**

```python
# Typical workflow integration
findings = run_phase1_regex_detection()
cmd_findings = [f for f in findings if f["type"] == "command_injection"]
other_findings = [f for f in findings if f["type"] != "command_injection"]

# Apply Phase 3 filtering
filtered_cmd = apply_phase3_filtering(cmd_findings)

# Combine results
final_findings = other_findings + filtered_cmd
```

---

## Configuration

### Environment Variables

```bash
# Enable debug logging
export ATTUNE_DEBUG=1

# Disable Phase 3 AST filtering (fallback to Phase 2)
export ATTUNE_DISABLE_PHASE3=1

# Custom scanner patterns file
export ATTUNE_SCANNER_PATTERNS=/path/to/patterns.json
```

### Configuration File

Create `empathy.config.yml` in project root:

```yaml
security_audit:
  # Exclude patterns (glob syntax)
  exclude:
    - "test_*"
    - ".venv/*"
    - "node_modules/*"
    - "*.min.js"

  # Include only specific patterns
  include:
    - "*.py"
    - "*.js"
    - "*.ts"

  # Severity thresholds (0-100)
  thresholds:
    critical: 90  # Score < 90 with critical findings
    medium: 70    # Score < 70 with medium findings
    low: 50       # Score < 50 with low findings

  # Scanner behavior
  scanner:
    enable_phase2: true   # Context-aware detection
    enable_phase3: true   # AST-based detection
    max_file_size: 1048576  # 1MB max file size
    timeout: 300          # 5 min timeout
```

---

## Return Types

### AuditResult

```python
from typing import TypedDict

class AuditResult(TypedDict):
    """Security audit result structure."""
    score: int                    # 0-100
    findings: list[Finding]       # Security findings
    summary: AuditSummary         # Summary statistics
    metadata: AuditMetadata       # Scan metadata

class Finding(TypedDict):
    """Individual security finding."""
    type: str                     # Vulnerability type
    severity: str                 # critical/medium/low
    file: str                     # File path
    line: int                     # Line number
    match: str                    # Matched text
    context: str                  # Surrounding code
    owasp: str                    # OWASP category
    description: str              # Description
    recommendation: str           # Fix recommendation

class AuditSummary(TypedDict):
    """Audit summary statistics."""
    total: int
    by_severity: dict[str, int]   # {"critical": 2, "medium": 5, ...}
    by_type: dict[str, int]       # {"sql_injection": 1, ...}

class AuditMetadata(TypedDict):
    """Scan metadata."""
    scan_time: float              # Duration in seconds
    files_scanned: int            # Number of files analyzed
    scanner_version: str          # Scanner version
    timestamp: str                # ISO 8601 timestamp
```

---

## Usage Examples

### Basic Scan

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

# Initialize workflow
workflow = SecurityAuditWorkflow()

# Run audit
results = workflow.run({"path": "./src"})

# Display results
print(f"Security Score: {results['score']}/100")
print(f"Total Findings: {results['summary']['total']}")

# Show critical findings
critical = [f for f in results['findings'] if f['severity'] == 'critical']
for finding in critical:
    print(f"\n❌ {finding['type']} in {finding['file']}:{finding['line']}")
    print(f"   {finding['description']}")
    print(f"   Fix: {finding['recommendation']}")
```

### CI/CD Integration

```python
import sys
from attune.workflows.security_audit import SecurityAuditWorkflow

def main():
    """Run security audit in CI/CD pipeline."""
    workflow = SecurityAuditWorkflow()
    results = workflow.run({"path": ".", "json_output": True})

    # Check for critical findings
    critical_count = results['summary']['by_severity'].get('critical', 0)

    if critical_count > 0:
        print(f"❌ FAILED: {critical_count} critical security issues found")
        for finding in results['findings']:
            if finding['severity'] == 'critical':
                print(f"  - {finding['file']}:{finding['line']} - {finding['type']}")
        sys.exit(1)  # Fail CI

    print(f"✅ PASSED: Security score {results['score']}/100")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Custom Analysis Pipeline

```python
from attune.workflows.security_audit import SecurityAuditWorkflow
from attune.workflows.security_audit_phase3 import (
    analyze_file_for_eval_exec,
    is_scanner_implementation_file,
)
from pathlib import Path

def custom_security_scan(directory: str):
    """Custom security scanning pipeline."""
    results = {
        "eval_exec_calls": [],
        "scanner_files": [],
        "other_findings": [],
    }

    # Scan all Python files
    for py_file in Path(directory).rglob("*.py"):
        file_str = str(py_file)

        # Check if scanner file
        if is_scanner_implementation_file(file_str):
            results["scanner_files"].append(file_str)
            continue  # Skip scanner files

        # Check for eval/exec calls
        findings = analyze_file_for_eval_exec(py_file)
        if findings:
            results["eval_exec_calls"].extend(findings)

    # Run full workflow for other vulnerabilities
    workflow = SecurityAuditWorkflow()
    audit_results = workflow.run({"path": directory})

    results["other_findings"] = [
        f for f in audit_results['findings']
        if f['type'] not in ('command_injection',)  # Already analyzed
    ]

    return results
```

### Extending with Custom Patterns

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

class CustomSecurityAudit(SecurityAuditWorkflow):
    """Extended security audit with custom patterns."""

    def __init__(self):
        super().__init__()

        # Add custom patterns
        self.PATTERNS["path_traversal"] = [
            r'open\s*\(\s*["\']?\.\./',  # Relative path with ../
            r'Path\s*\([^)]*\.\./[^)]*\)',  # Path with ../
        ]

        self.PATTERNS["weak_crypto"] = [
            r'hashlib\.md5\(',   # MD5 is weak
            r'hashlib\.sha1\(',  # SHA1 is weak
        ]

    def _is_safe_path_usage(self, line: str, context: str) -> bool:
        """Check if path usage is safe."""
        # Check for _validate_file_path usage
        if "_validate_file_path" in context:
            return True

        # Check for security note
        if "security note" in context.lower():
            return True

        return False

    def _triage(self, findings: list[dict]) -> list[dict]:
        """Enhanced triage with custom filtering."""
        # Apply parent class triage
        filtered = super()._triage(findings)

        # Apply custom filtering
        final = []
        for finding in filtered:
            if finding['type'] == 'path_traversal':
                if self._is_safe_path_usage(
                    finding['context'],
                    finding.get('file_content', '')
                ):
                    continue  # Safe usage

            final.append(finding)

        return final

# Usage
custom_workflow = CustomSecurityAudit()
results = custom_workflow.run({"path": "./src"})
```

---

## Extension Guide

### Adding New Vulnerability Detection

1. **Define Regex Pattern**

```python
# In SecurityAuditWorkflow class
PATTERNS = {
    "your_vulnerability_type": [
        r'pattern1',
        r'pattern2',
    ],
}
```

2. **Add Context-Aware Filter (Optional)**

```python
def _is_safe_your_pattern(self, line: str, file_path: str, context: str) -> bool:
    """Determine if pattern is actually safe."""
    # Add your filtering logic
    return False
```

3. **Integrate in Triage**

```python
def _triage(self, findings: list[dict]) -> list[dict]:
    filtered = []
    for finding in findings:
        if finding['type'] == 'your_vulnerability_type':
            if self._is_safe_your_pattern(
                finding['context'],
                finding['file'],
                finding.get('file_content', '')
            ):
                continue  # Skip safe patterns
        filtered.append(finding)
    return filtered
```

4. **Add Tests**

```python
def test_your_vulnerability_detection():
    """Test custom vulnerability detection."""
    workflow = SecurityAuditWorkflow()

    # Test unsafe pattern
    unsafe_code = "..."
    results = workflow.run({"path": "test_file.py"})
    assert any(f['type'] == 'your_vulnerability_type' for f in results['findings'])

    # Test safe pattern
    safe_code = "..."
    # Should not be flagged
```

---

## Performance Tips

### Optimize Large Codebases

```python
# Use exclusions to skip unnecessary files
results = workflow.run({
    "path": ".",
    "exclude": [
        ".venv/*",
        "node_modules/*",
        "*.min.js",
        "dist/*",
        "build/*",
    ]
})

# Scan specific subdirectories in parallel
from concurrent.futures import ThreadPoolExecutor

def scan_directory(path: str) -> dict:
    workflow = SecurityAuditWorkflow()
    return workflow.run({"path": path})

with ThreadPoolExecutor(max_workers=4) as executor:
    paths = ["src/", "tests/", "scripts/"]
    results = list(executor.map(scan_directory, paths))
```

### Cache AST Parsing

```python
from functools import lru_cache
import ast

@lru_cache(maxsize=500)
def parse_python_file(file_path: str, file_hash: str) -> ast.Module:
    """Cache AST parsing results."""
    with open(file_path) as f:
        return ast.parse(f.read())

# Use in your analysis
file_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
tree = parse_python_file(file_path, file_hash)
```

---

## Error Handling

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

try:
    workflow = SecurityAuditWorkflow()
    results = workflow.run({"path": "./src"})

except ValueError as e:
    print(f"Configuration error: {e}")
    # Path does not exist, invalid config, etc.

except PermissionError as e:
    print(f"Permission denied: {e}")
    # Cannot read files, insufficient permissions

except Exception as e:
    print(f"Unexpected error: {e}")
    # Log and report bug
```

---

## Changelog

### v1.0 (2026-01-26)
- Initial API documentation
- Phase 1-3 complete
- CI/CD integration ready

---

## See Also

- [SECURITY_SCANNER_ARCHITECTURE.md](../SECURITY_SCANNER_ARCHITECTURE.md) - Architecture overview
- [CI_SECURITY_SCANNING.md](../CI_SECURITY_SCANNING.md) - CI/CD guide
- [CODING_STANDARDS.md](../CODING_STANDARDS.md) - Security coding standards

---

**API Version:** 1.0
**Stability:** Stable
**Support:** security-team@company.com
