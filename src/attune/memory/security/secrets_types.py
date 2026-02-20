"""Type definitions for the Secrets Detection Module.

Defines SecretType enum, Severity enum, and SecretDetection
dataclass used by the secrets detector.

Author: Attune AI Team
Version: 1.8.0-beta
License: Apache License 2.0
"""

from dataclasses import dataclass, field
from enum import Enum


class SecretType(Enum):
    """Types of secrets that can be detected"""

    # API Keys
    ANTHROPIC_API_KEY = "anthropic_api_key"
    OPENAI_API_KEY = "openai_api_key"
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    GITHUB_TOKEN = "github_token"
    SLACK_TOKEN = "slack_token"
    STRIPE_KEY = "stripe_key"
    GENERIC_API_KEY = "generic_api_key"

    # Passwords
    PASSWORD = "password"
    BASIC_AUTH = "basic_auth"

    # Private Keys
    RSA_PRIVATE_KEY = "rsa_private_key"
    SSH_PRIVATE_KEY = "ssh_private_key"
    EC_PRIVATE_KEY = "ec_private_key"
    PGP_PRIVATE_KEY = "pgp_private_key"
    TLS_CERTIFICATE_KEY = "tls_certificate_key"

    # Tokens
    JWT_TOKEN = "jwt_token"
    OAUTH_TOKEN = "oauth_token"
    BEARER_TOKEN = "bearer_token"

    # Database
    DATABASE_URL = "database_url"
    CONNECTION_STRING = "connection_string"

    # High Entropy
    HIGH_ENTROPY_STRING = "high_entropy_string"


class Severity(Enum):
    """Severity levels for secret detections"""

    CRITICAL = "critical"  # Private keys, AWS credentials
    HIGH = "high"  # API keys, passwords
    MEDIUM = "medium"  # OAuth tokens, JWT
    LOW = "low"  # Potential secrets, high entropy strings


@dataclass
class SecretDetection:
    """Metadata about a detected secret.

    CRITICAL: The actual secret value is NEVER stored in this object.
    """

    secret_type: SecretType
    severity: Severity
    line_number: int
    column_start: int
    column_end: int
    context_snippet: str = ""  # Surrounding text (without the secret itself)
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization"""
        return {
            "secret_type": self.secret_type.value,
            "severity": self.severity.value,
            "line_number": self.line_number,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "context_snippet": self.context_snippet,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
