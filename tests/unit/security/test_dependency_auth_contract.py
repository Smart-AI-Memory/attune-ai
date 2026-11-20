"""JWT security contracts and defense-in-depth invariants."""

import base64
import hashlib
import hmac
import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def test_reusing_options_preserves_expiration_verification():
    """GHSA-gvp8-978c-rx2q: unverified peeks must not disable claim checks."""
    key = b"x" * 32
    token = jwt.encode({"sub": "test-user", "exp": 0}, key, algorithm="HS256")
    options = {"verify_signature": False}

    assert jwt.decode(token, options=options)["sub"] == "test-user"
    assert options == {"verify_signature": False}

    options["verify_signature"] = True
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, key, algorithms=["HS256"], options=options)


@pytest.fixture(scope="module")
def public_key_pem():
    """Generate ephemeral public material without storing a private key."""
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )


@pytest.mark.parametrize("variant", ["whitespace", "bom", "crlf"])
def test_public_key_material_cannot_verify_hmac_tokens(public_key_pem, variant):
    """Guard asymmetric-key rejection; this is not a listed advisory reproducer."""
    if variant == "whitespace":
        material = b" \t\n" + public_key_pem
    elif variant == "bom":
        material = b"\xef\xbb\xbf" + public_key_pem
    else:
        material = public_key_pem.replace(b"\n", b"\r\n")

    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=")
    payload = {"sub": "test-user"}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    signing_input = header + b"." + body
    signature = base64.urlsafe_b64encode(
        hmac.new(material, signing_input, hashlib.sha256).digest()
    ).rstrip(b"=")
    forged = (signing_input + b"." + signature).decode("ascii")

    with pytest.raises(jwt.InvalidKeyError, match="asymmetric key"):
        jwt.decode(forged, material, algorithms=["HS256"])

    legitimate_key = b"x" * 32
    legitimate = jwt.encode(payload, legitimate_key, algorithm="HS256")
    assert jwt.decode(legitimate, legitimate_key, algorithms=["HS256"]) == payload
