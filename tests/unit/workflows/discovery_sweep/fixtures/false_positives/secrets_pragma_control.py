"""Control: hardcoded secret WITHOUT the pragma comment.

This IS a real finding. The rule must NOT fire here.
"""

# Real bug — secret pinned in source without an allowlist pragma.
LEAKED_API_KEY = "sk_live_realLookingSecret_xyz789"
