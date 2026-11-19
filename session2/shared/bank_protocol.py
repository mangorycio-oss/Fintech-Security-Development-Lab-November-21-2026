import base64
import hashlib
import os

PKCE_PATTERN = r"^[A-Za-z0-9._~-]{43,128}$"
CLIENT_ID = "fintech-lab"
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/section-2/bank/callback")
SCOPES = {"accounts:read", "payments:write"}


def pkce_challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
