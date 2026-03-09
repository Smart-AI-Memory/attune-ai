"""Tests for attune/agent_factory/crews/security_audit/

Tests the security audit crew including:
- Severity enum
- FindingCategory enum (OWASP-aligned)
- SecurityFinding dataclass
- SecurityReport dataclass
- SecurityAuditConfig dataclass
- Parsers (dict_to_finding, parse_findings, parse_text_findings, generate_summary)
- SecurityAuditCrew (task building, initialization)
"""

from unittest.mock import patch

import pytest

from attune.agent_factory.crews.security_audit import (
    FindingCategory,
    SecurityAuditConfig,
    SecurityAuditCrew,
    SecurityFinding,
    SecurityReport,
    Severity,
)
from attune.agent_factory.crews.security_audit.parsers import (
    dict_to_finding,
    generate_summary,
    parse_findings,
    parse_text_findings,
)

# -------------------------------------------------------------------
# Severity Enum
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_critical_value(self):
        """Test CRITICAL severity value."""
        assert Severity.CRITICAL.value == "critical"

    def test_high_value(self):
        """Test HIGH severity value."""
        assert Severity.HIGH.value == "high"

    def test_medium_value(self):
        """Test MEDIUM severity value."""
        assert Severity.MEDIUM.value == "medium"

    def test_low_value(self):
        """Test LOW severity value."""
        assert Severity.LOW.value == "low"

    def test_info_value(self):
        """Test INFO severity value."""
        assert Severity.INFO.value == "info"

    def test_all_severities_count(self):
        """Test total number of severity levels."""
        assert len(Severity) == 5

    def test_severity_from_string(self):
        """Test constructing Severity from string value."""
        assert Severity("critical") == Severity.CRITICAL
        assert Severity("high") == Severity.HIGH
        assert Severity("medium") == Severity.MEDIUM


# -------------------------------------------------------------------
# FindingCategory Enum
# -------------------------------------------------------------------


@pytest.mark.unit
class TestFindingCategoryEnum:
    """Tests for FindingCategory enum (OWASP-aligned)."""

    def test_injection_value(self):
        """Test INJECTION category value."""
        assert FindingCategory.INJECTION.value == "injection"

    def test_broken_auth_value(self):
        """Test BROKEN_AUTH category value."""
        assert FindingCategory.BROKEN_AUTH.value == "broken_authentication"

    def test_sensitive_data_value(self):
        """Test SENSITIVE_DATA category value."""
        assert FindingCategory.SENSITIVE_DATA.value == "sensitive_data_exposure"

    def test_xxe_value(self):
        """Test XXE category value."""
        assert FindingCategory.XXE.value == "xml_external_entities"

    def test_broken_access_value(self):
        """Test BROKEN_ACCESS category value."""
        assert FindingCategory.BROKEN_ACCESS.value == "broken_access_control"

    def test_misconfiguration_value(self):
        """Test MISCONFIGURATION category value."""
        assert FindingCategory.MISCONFIGURATION.value == "security_misconfiguration"

    def test_xss_value(self):
        """Test XSS category value."""
        assert FindingCategory.XSS.value == "cross_site_scripting"

    def test_insecure_deserialization_value(self):
        """Test INSECURE_DESERIALIZATION category value."""
        assert FindingCategory.INSECURE_DESERIALIZATION.value == "insecure_deserialization"

    def test_vulnerable_components_value(self):
        """Test VULNERABLE_COMPONENTS category value."""
        assert FindingCategory.VULNERABLE_COMPONENTS.value == "vulnerable_components"

    def test_insufficient_logging_value(self):
        """Test INSUFFICIENT_LOGGING category value."""
        assert FindingCategory.INSUFFICIENT_LOGGING.value == "insufficient_logging"

    def test_other_value(self):
        """Test OTHER category value."""
        assert FindingCategory.OTHER.value == "other"

    def test_all_categories_count(self):
        """Test total number of OWASP-aligned categories."""
        assert len(FindingCategory) == 11

    def test_category_from_string(self):
        """Test constructing FindingCategory from string value."""
        assert FindingCategory("injection") == FindingCategory.INJECTION
        assert FindingCategory("other") == FindingCategory.OTHER


# -------------------------------------------------------------------
# SecurityFinding Dataclass
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_basic_creation(self):
        """Test basic finding creation with required fields."""
        finding = SecurityFinding(
            title="SQL Injection",
            description="User input in raw SQL query",
            severity=Severity.CRITICAL,
            category=FindingCategory.INJECTION,
        )
        assert finding.title == "SQL Injection"
        assert finding.description == "User input in raw SQL query"
        assert finding.severity == Severity.CRITICAL
        assert finding.category == FindingCategory.INJECTION

    def test_optional_fields_default_none(self):
        """Test optional fields default to None."""
        finding = SecurityFinding(
            title="Test",
            description="Test desc",
            severity=Severity.LOW,
            category=FindingCategory.OTHER,
        )
        assert finding.file_path is None
        assert finding.line_number is None
        assert finding.code_snippet is None
        assert finding.remediation is None
        assert finding.cwe_id is None
        assert finding.cvss_score is None

    def test_confidence_defaults_to_one(self):
        """Test confidence defaults to 1.0."""
        finding = SecurityFinding(
            title="Test",
            description="Test",
            severity=Severity.INFO,
            category=FindingCategory.OTHER,
        )
        assert finding.confidence == 1.0

    def test_metadata_defaults_to_empty_dict(self):
        """Test metadata defaults to empty dict."""
        finding = SecurityFinding(
            title="Test",
            description="Test",
            severity=Severity.LOW,
            category=FindingCategory.OTHER,
        )
        assert finding.metadata == {}

    def test_full_finding_creation(self):
        """Test finding with all fields populated."""
        finding = SecurityFinding(
            title="Hardcoded Secret",
            description="API key hardcoded in source",
            severity=Severity.HIGH,
            category=FindingCategory.SENSITIVE_DATA,
            file_path="src/config.py",
            line_number=42,
            code_snippet='API_KEY = "sk_live_..."',
            remediation="Use environment variables",
            cwe_id="CWE-798",
            cvss_score=7.5,
            confidence=0.95,
            metadata={"detector": "secrets_scanner"},
        )
        assert finding.file_path == "src/config.py"
        assert finding.line_number == 42
        assert finding.cwe_id == "CWE-798"
        assert finding.cvss_score == 7.5
        assert finding.confidence == 0.95
        assert finding.metadata["detector"] == "secrets_scanner"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        finding = SecurityFinding(
            title="XSS Vulnerability",
            description="Unsanitized input in template",
            severity=Severity.HIGH,
            category=FindingCategory.XSS,
            file_path="src/views.py",
            line_number=88,
            cwe_id="CWE-79",
        )
        data = finding.to_dict()
        assert data["title"] == "XSS Vulnerability"
        assert data["severity"] == "high"
        assert data["category"] == "cross_site_scripting"
        assert data["file_path"] == "src/views.py"
        assert data["line_number"] == 88
        assert data["cwe_id"] == "CWE-79"

    def test_to_dict_includes_all_fields(self):
        """Test to_dict includes all expected fields."""
        finding = SecurityFinding(
            title="Test",
            description="Test",
            severity=Severity.LOW,
            category=FindingCategory.OTHER,
        )
        data = finding.to_dict()
        expected_keys = [
            "title",
            "description",
            "severity",
            "category",
            "file_path",
            "line_number",
            "code_snippet",
            "remediation",
            "cwe_id",
            "cvss_score",
            "confidence",
            "metadata",
        ]
        for key in expected_keys:
            assert key in data

    def test_to_dict_enum_values_are_strings(self):
        """Test that enum values are serialized as strings."""
        finding = SecurityFinding(
            title="Test",
            description="Test",
            severity=Severity.CRITICAL,
            category=FindingCategory.INJECTION,
        )
        data = finding.to_dict()
        assert isinstance(data["severity"], str)
        assert isinstance(data["category"], str)


# -------------------------------------------------------------------
# SecurityReport Dataclass
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityReport:
    """Tests for SecurityReport dataclass."""

    def test_basic_creation(self):
        """Test basic report creation."""
        report = SecurityReport(
            target="./src",
            findings=[],
        )
        assert report.target == "./src"
        assert report.findings == []

    def test_default_values(self):
        """Test default values."""
        report = SecurityReport(target="test", findings=[])
        assert report.summary == ""
        assert report.audit_duration_seconds == 0.0
        assert report.agents_used == []
        assert report.memory_graph_hits == 0
        assert report.metadata == {}

    def test_critical_findings_property(self):
        """Test critical_findings property filters correctly."""
        findings = [
            SecurityFinding("Critical 1", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
            SecurityFinding("High 1", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("Critical 2", "Desc", Severity.CRITICAL, FindingCategory.BROKEN_AUTH),
            SecurityFinding("Low 1", "Desc", Severity.LOW, FindingCategory.OTHER),
        ]
        report = SecurityReport(target="test", findings=findings)
        critical = report.critical_findings
        assert len(critical) == 2
        assert all(f.severity == Severity.CRITICAL for f in critical)

    def test_critical_findings_empty_when_none(self):
        """Test critical_findings returns empty list when no critical findings."""
        findings = [
            SecurityFinding("High 1", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("Medium 1", "Desc", Severity.MEDIUM, FindingCategory.OTHER),
        ]
        report = SecurityReport(target="test", findings=findings)
        assert report.critical_findings == []

    def test_high_findings_property(self):
        """Test high_findings property filters correctly."""
        findings = [
            SecurityFinding("Critical 1", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
            SecurityFinding("High 1", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("High 2", "Desc", Severity.HIGH, FindingCategory.SENSITIVE_DATA),
            SecurityFinding("Medium 1", "Desc", Severity.MEDIUM, FindingCategory.OTHER),
        ]
        report = SecurityReport(target="test", findings=findings)
        high = report.high_findings
        assert len(high) == 2
        assert all(f.severity == Severity.HIGH for f in high)

    def test_findings_by_category_property(self):
        """Test findings_by_category groups correctly."""
        findings = [
            SecurityFinding("Inj 1", "Desc", Severity.HIGH, FindingCategory.INJECTION),
            SecurityFinding("Inj 2", "Desc", Severity.MEDIUM, FindingCategory.INJECTION),
            SecurityFinding("XSS 1", "Desc", Severity.LOW, FindingCategory.XSS),
            SecurityFinding("Auth 1", "Desc", Severity.MEDIUM, FindingCategory.BROKEN_AUTH),
        ]
        report = SecurityReport(target="test", findings=findings)
        by_cat = report.findings_by_category
        assert len(by_cat["injection"]) == 2
        assert len(by_cat["cross_site_scripting"]) == 1
        assert len(by_cat["broken_authentication"]) == 1

    def test_findings_by_category_empty(self):
        """Test findings_by_category with no findings."""
        report = SecurityReport(target="test", findings=[])
        assert report.findings_by_category == {}

    def test_risk_score_empty_findings(self):
        """Test risk_score is 0 with no findings."""
        report = SecurityReport(target="test", findings=[])
        assert report.risk_score == 0.0

    def test_risk_score_single_critical(self):
        """Test risk_score with a single critical finding."""
        findings = [
            SecurityFinding("Critical", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
        ]
        report = SecurityReport(target="test", findings=findings)
        # CRITICAL weight = 25, confidence = 1.0 => score = 25.0
        assert report.risk_score == 25.0

    def test_risk_score_mixed_findings(self):
        """Test risk_score with mixed severity findings."""
        findings = [
            SecurityFinding("Critical", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
            SecurityFinding("High", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("Medium", "Desc", Severity.MEDIUM, FindingCategory.OTHER),
        ]
        report = SecurityReport(target="test", findings=findings)
        # CRITICAL=25 + HIGH=15 + MEDIUM=5 = 45.0
        assert report.risk_score == 45.0

    def test_risk_score_respects_confidence(self):
        """Test risk_score factors in confidence."""
        findings = [
            SecurityFinding(
                "Critical",
                "Desc",
                Severity.CRITICAL,
                FindingCategory.INJECTION,
                confidence=0.5,
            ),
        ]
        report = SecurityReport(target="test", findings=findings)
        # CRITICAL weight=25, confidence=0.5 => 12.5
        assert report.risk_score == 12.5

    def test_risk_score_capped_at_100(self):
        """Test risk_score doesn't exceed 100."""
        findings = [
            SecurityFinding(f"Critical {i}", "Desc", Severity.CRITICAL, FindingCategory.INJECTION)
            for i in range(10)
        ]
        report = SecurityReport(target="test", findings=findings)
        # 10 * 25 = 250, but capped at 100
        assert report.risk_score == 100.0

    def test_to_dict(self):
        """Test report serialization to dictionary."""
        findings = [
            SecurityFinding("SQL Injection", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
            SecurityFinding("XSS", "Desc", Severity.HIGH, FindingCategory.XSS),
        ]
        report = SecurityReport(
            target="./src",
            findings=findings,
            summary="2 issues found",
            audit_duration_seconds=30.5,
            agents_used=["lead", "hunter"],
            memory_graph_hits=2,
            metadata={"scan_depth": "standard"},
        )
        data = report.to_dict()
        assert data["target"] == "./src"
        assert data["summary"] == "2 issues found"
        assert data["audit_duration_seconds"] == 30.5
        assert data["agents_used"] == ["lead", "hunter"]
        assert data["memory_graph_hits"] == 2
        assert data["risk_score"] == 40.0  # 25 + 15
        assert data["finding_counts"]["critical"] == 1
        assert data["finding_counts"]["high"] == 1
        assert data["finding_counts"]["total"] == 2
        assert len(data["findings"]) == 2
        assert data["metadata"]["scan_depth"] == "standard"

    def test_to_dict_empty_report(self):
        """Test to_dict on report with no findings."""
        report = SecurityReport(target="test", findings=[])
        data = report.to_dict()
        assert data["risk_score"] == 0.0
        assert data["finding_counts"]["critical"] == 0
        assert data["finding_counts"]["total"] == 0
        assert data["findings"] == []

    def test_report_with_agents_and_metadata(self):
        """Test report with agents and metadata."""
        report = SecurityReport(
            target="./project",
            findings=[],
            summary="Clean scan",
            audit_duration_seconds=120.0,
            agents_used=["lead", "hunter", "assessor", "remediation", "compliance"],
            memory_graph_hits=5,
            metadata={"framework": "crewai"},
        )
        assert len(report.agents_used) == 5
        assert report.memory_graph_hits == 5
        assert report.audit_duration_seconds == 120.0
        assert report.metadata["framework"] == "crewai"


# -------------------------------------------------------------------
# SecurityAuditConfig Dataclass
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityAuditConfig:
    """Tests for SecurityAuditConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SecurityAuditConfig()
        assert config.provider == "anthropic"
        assert config.api_key is None
        assert config.scan_depth == "standard"
        assert config.memory_graph_enabled is True
        assert config.resilience_enabled is True
        assert config.timeout_seconds == 300.0
        assert config.xml_prompts_enabled is True
        assert config.xml_schema_version == "1.0"

    def test_default_include_patterns(self):
        """Test default include patterns."""
        config = SecurityAuditConfig()
        assert "*.py" in config.include_patterns
        assert "*.js" in config.include_patterns
        assert "*.ts" in config.include_patterns

    def test_default_exclude_patterns(self):
        """Test default exclude patterns."""
        config = SecurityAuditConfig()
        assert "*test*" in config.exclude_patterns
        assert "node_modules/*" in config.exclude_patterns

    def test_default_tier_assignments(self):
        """Test default agent tier assignments."""
        config = SecurityAuditConfig()
        assert config.lead_tier == "premium"
        assert config.hunter_tier == "capable"
        assert config.assessor_tier == "capable"
        assert config.remediation_tier == "premium"
        assert config.compliance_tier == "cheap"

    def test_custom_values(self):
        """Test config with custom values."""
        config = SecurityAuditConfig(
            provider="openai",
            scan_depth="thorough",
            memory_graph_enabled=False,
            timeout_seconds=600.0,
            lead_tier="capable",
        )
        assert config.provider == "openai"
        assert config.scan_depth == "thorough"
        assert config.memory_graph_enabled is False
        assert config.timeout_seconds == 600.0
        assert config.lead_tier == "capable"

    def test_custom_include_patterns(self):
        """Test config with custom include patterns."""
        config = SecurityAuditConfig(include_patterns=["*.rs", "*.c"])
        assert config.include_patterns == ["*.rs", "*.c"]


# -------------------------------------------------------------------
# Parsers
# -------------------------------------------------------------------


@pytest.mark.unit
class TestDictToFinding:
    """Tests for dict_to_finding parser."""

    def test_happy_path(self):
        """Test converting a fully populated dict to SecurityFinding."""
        data = {
            "title": "SQL Injection",
            "description": "Unsanitized user input in query",
            "severity": "critical",
            "category": "injection",
            "file_path": "src/db.py",
            "line_number": 42,
            "code_snippet": "cursor.execute(f'SELECT * FROM {user_input}')",
            "remediation": "Use parameterized queries",
            "cwe_id": "CWE-89",
            "cvss_score": 9.8,
            "confidence": 0.99,
            "metadata": {"tool": "semgrep"},
        }
        finding = dict_to_finding(data)
        assert finding.title == "SQL Injection"
        assert finding.severity == Severity.CRITICAL
        assert finding.category == FindingCategory.INJECTION
        assert finding.file_path == "src/db.py"
        assert finding.cwe_id == "CWE-89"
        assert finding.cvss_score == 9.8
        assert finding.confidence == 0.99

    def test_defaults_for_missing_fields(self):
        """Test defaults when dict has minimal fields."""
        data = {}
        finding = dict_to_finding(data)
        assert finding.title == "Untitled Finding"
        assert finding.description == ""
        assert finding.severity == Severity.MEDIUM
        assert finding.category == FindingCategory.OTHER
        assert finding.file_path is None
        assert finding.line_number is None
        assert finding.confidence == 1.0
        assert finding.metadata == {}

    def test_partial_data(self):
        """Test with partial data."""
        data = {
            "title": "Weak Password Policy",
            "severity": "low",
            "category": "broken_authentication",
        }
        finding = dict_to_finding(data)
        assert finding.title == "Weak Password Policy"
        assert finding.severity == Severity.LOW
        assert finding.category == FindingCategory.BROKEN_AUTH


@pytest.mark.unit
class TestParseFindings:
    """Tests for parse_findings function."""

    def test_structured_metadata(self):
        """Test parsing structured findings from metadata."""
        result = {
            "metadata": {
                "findings": [
                    {"title": "Finding 1", "severity": "high", "category": "injection"},
                    {"title": "Finding 2", "severity": "low", "category": "other"},
                ],
            },
        }
        findings = parse_findings(result)
        assert len(findings) == 2
        assert findings[0].title == "Finding 1"
        assert findings[0].severity == Severity.HIGH
        assert findings[1].title == "Finding 2"

    def test_text_fallback(self):
        """Test falling back to text parsing when no structured metadata."""
        result = {
            "output": "Critical vulnerability detected in auth module\n"
            "High severity issue found in session handling",
        }
        findings = parse_findings(result)
        # Should parse at least one finding from text
        assert len(findings) >= 1

    def test_empty_result(self):
        """Test parsing empty result dict."""
        result = {}
        findings = parse_findings(result)
        assert findings == []

    def test_empty_metadata(self):
        """Test parsing result with empty metadata (no findings key)."""
        result = {"metadata": {}, "output": ""}
        findings = parse_findings(result)
        assert findings == []

    def test_metadata_takes_precedence_over_text(self):
        """Test that structured metadata is preferred over text parsing."""
        result = {
            "metadata": {
                "findings": [
                    {"title": "Structured Finding", "severity": "critical"},
                ],
            },
            "output": "Some text vulnerability detected",
        }
        findings = parse_findings(result)
        assert len(findings) == 1
        assert findings[0].title == "Structured Finding"


@pytest.mark.unit
class TestParseTextFindings:
    """Tests for parse_text_findings function."""

    def test_multiple_findings(self):
        """Test parsing multiple findings from text."""
        text = (
            "Critical vulnerability detected in auth.py\n" "High severity issue detected in db.py\n"
        )
        findings = parse_text_findings(text)
        assert len(findings) >= 2

    def test_severity_detection_critical(self):
        """Test detection of critical severity keyword."""
        text = "Critical vulnerability detected in authentication"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_severity_detection_high(self):
        """Test detection of high severity keyword."""
        text = "High severity issue detected in session management"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_severity_detection_info(self):
        """Test detection of informational severity keyword."""
        text = "Informational finding detected: best practice recommendation"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO

    def test_category_detection_injection(self):
        """Test detection of injection category."""
        text = "SQL injection vulnerability detected in query builder"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.INJECTION

    def test_category_detection_xss(self):
        """Test detection of XSS category."""
        text = "Cross-site scripting issue detected in template"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.XSS

    def test_category_detection_auth(self):
        """Test detection of broken authentication category."""
        text = "Authentication vulnerability detected in login handler"
        findings = parse_text_findings(text)
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.BROKEN_AUTH

    def test_empty_text(self):
        """Test parsing empty text."""
        findings = parse_text_findings("")
        assert findings == []

    def test_no_indicators_in_text(self):
        """Test text without finding indicator keywords."""
        text = "All systems are secure. No problems found."
        findings = parse_text_findings(text)
        assert findings == []

    def test_title_truncation(self):
        """Test that titles are truncated to 100 characters."""
        long_line = "A" * 200 + " vulnerability detected"
        findings = parse_text_findings(long_line)
        if findings:
            assert len(findings[0].title) <= 100


@pytest.mark.unit
class TestGenerateSummary:
    """Tests for generate_summary function."""

    def test_empty_findings(self):
        """Test summary with no findings."""
        summary = generate_summary([])
        assert "No security issues" in summary

    def test_single_critical_finding(self):
        """Test summary with one critical finding."""
        findings = [
            SecurityFinding(
                "RCE", "Remote code execution", Severity.CRITICAL, FindingCategory.INJECTION
            ),
        ]
        summary = generate_summary(findings)
        assert "1 findings" in summary or "1 finding" in summary
        assert "CRITICAL" in summary
        assert "immediate action" in summary

    def test_mixed_findings(self):
        """Test summary with mixed severities."""
        findings = [
            SecurityFinding("F1", "Desc", Severity.CRITICAL, FindingCategory.INJECTION),
            SecurityFinding("F2", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("F3", "Desc", Severity.HIGH, FindingCategory.XSS),
            SecurityFinding("F4", "Desc", Severity.MEDIUM, FindingCategory.OTHER),
            SecurityFinding("F5", "Desc", Severity.LOW, FindingCategory.MISCONFIGURATION),
        ]
        summary = generate_summary(findings)
        assert "5 findings" in summary
        assert "CRITICAL" in summary
        assert "HIGH" in summary
        assert "MEDIUM" in summary
        assert "LOW" in summary

    def test_summary_includes_top_categories(self):
        """Test summary includes top vulnerability categories."""
        findings = [
            SecurityFinding("F1", "Desc", Severity.HIGH, FindingCategory.INJECTION),
            SecurityFinding("F2", "Desc", Severity.HIGH, FindingCategory.INJECTION),
            SecurityFinding("F3", "Desc", Severity.MEDIUM, FindingCategory.XSS),
        ]
        summary = generate_summary(findings)
        assert "Top vulnerability categories" in summary
        assert "injection" in summary

    def test_info_findings_not_in_breakdown(self):
        """Test that INFO findings are not listed in the breakdown."""
        findings = [
            SecurityFinding("F1", "Desc", Severity.INFO, FindingCategory.OTHER),
        ]
        summary = generate_summary(findings)
        # INFO is not included in the severity breakdown
        assert "CRITICAL" not in summary
        assert "HIGH" not in summary


# -------------------------------------------------------------------
# SecurityAuditCrew
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityAuditCrew:
    """Tests for SecurityAuditCrew class."""

    def test_config_class_attribute(self):
        """Test that config_class is SecurityAuditConfig."""
        assert SecurityAuditCrew.config_class is SecurityAuditConfig

    def test_xml_prompt_templates_attribute(self):
        """Test that XML_PROMPT_TEMPLATES is set."""
        assert isinstance(SecurityAuditCrew.XML_PROMPT_TEMPLATES, dict)
        assert len(SecurityAuditCrew.XML_PROMPT_TEMPLATES) > 0

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_build_audit_task_basic(self, mock_init):
        """Test _build_audit_task generates task with target and config."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        task = crew._build_audit_task("./src", {})
        assert "./src" in task
        assert "standard" in task
        assert "*.py" in task

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_build_audit_task_with_context_similar_audits(self, mock_init):
        """Test _build_audit_task includes similar audit context."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        context = {"similar_audits": [{"name": "audit:old", "findings_count": 3}]}
        task = crew._build_audit_task("./src", context)
        assert "Previous Similar Audits Found" in task

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_build_audit_task_with_focus_areas(self, mock_init):
        """Test _build_audit_task includes focus areas."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        context = {"focus_areas": ["authentication", "injection"]}
        task = crew._build_audit_task("./src", context)
        assert "Focus Areas Requested" in task
        assert "authentication" in task
        assert "injection" in task

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_build_audit_task_scan_depth_quick(self, mock_init):
        """Test _build_audit_task with quick scan depth."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig(scan_depth="quick")
        task = crew._build_audit_task("./src", {})
        assert "quick" in task.lower()
        assert "critical and high" in task.lower()

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_build_audit_task_scan_depth_thorough(self, mock_init):
        """Test _build_audit_task with thorough scan depth."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig(scan_depth="thorough")
        task = crew._build_audit_task("./src", {})
        assert "thorough" in task.lower()
        assert "deep analysis" in task.lower()

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_delegation_methods_exist(self, mock_init):
        """Test backward-compatible delegation methods are available."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        assert hasattr(crew, "_parse_findings")
        assert hasattr(crew, "_dict_to_finding")
        assert hasattr(crew, "_parse_text_findings")
        assert hasattr(crew, "_generate_summary")

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_delegation_parse_findings(self, mock_init):
        """Test _parse_findings delegation works."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        result = {
            "metadata": {
                "findings": [{"title": "Test", "severity": "low"}],
            },
        }
        findings = crew._parse_findings(result)
        assert len(findings) == 1
        assert findings[0].title == "Test"

    @patch(
        "attune.agent_factory.crews.security_audit.crew.CrewBase.__init__",
        return_value=None,
    )
    def test_delegation_generate_summary(self, mock_init):
        """Test _generate_summary delegation works."""
        crew = SecurityAuditCrew.__new__(SecurityAuditCrew)
        crew.config = SecurityAuditConfig()
        summary = crew._generate_summary([])
        assert "No security issues" in summary


# -------------------------------------------------------------------
# Integration
# -------------------------------------------------------------------


@pytest.mark.unit
class TestSecurityAuditIntegration:
    """Integration tests for security audit components working together."""

    def test_complete_audit_flow(self):
        """Test creating a complete report with multiple findings."""
        findings = [
            SecurityFinding(
                title="SQL Injection in User Search",
                description="User input concatenated into SQL query",
                severity=Severity.CRITICAL,
                category=FindingCategory.INJECTION,
                file_path="src/search.py",
                line_number=45,
                remediation="Use parameterized queries",
                cwe_id="CWE-89",
                cvss_score=9.8,
            ),
            SecurityFinding(
                title="Missing CSRF Token",
                description="Form submission lacks CSRF protection",
                severity=Severity.HIGH,
                category=FindingCategory.XSS,
                file_path="src/forms.py",
                line_number=22,
                remediation="Add CSRF middleware",
            ),
            SecurityFinding(
                title="Debug Mode Enabled",
                description="Production config has DEBUG=True",
                severity=Severity.MEDIUM,
                category=FindingCategory.MISCONFIGURATION,
                file_path="settings.py",
                line_number=5,
            ),
            SecurityFinding(
                title="Verbose Error Messages",
                description="Stack traces exposed to users",
                severity=Severity.LOW,
                category=FindingCategory.SENSITIVE_DATA,
            ),
        ]

        report = SecurityReport(
            target="./web-app",
            findings=findings,
            summary=generate_summary(findings),
            agents_used=["lead", "hunter", "assessor", "remediation", "compliance"],
            audit_duration_seconds=60.0,
        )

        # Verify report structure
        assert len(report.findings) == 4
        assert len(report.critical_findings) == 1
        assert len(report.high_findings) == 1
        assert report.risk_score == 47.0  # 25 + 15 + 5 + 2

        # Verify category grouping
        by_cat = report.findings_by_category
        assert "injection" in by_cat
        assert "cross_site_scripting" in by_cat
        assert "security_misconfiguration" in by_cat

        # Verify serialization
        data = report.to_dict()
        assert data["finding_counts"]["critical"] == 1
        assert data["finding_counts"]["total"] == 4
        assert data["risk_score"] == 47.0

        # Verify summary
        assert "CRITICAL" in report.summary
        assert "HIGH" in report.summary
