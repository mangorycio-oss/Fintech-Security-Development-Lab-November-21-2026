from datetime import datetime, timedelta, timezone
import unittest

import jwt

from web.security.jwt import AUDIENCE, ISSUER, KEY
from tests import login, request


class JWTTests(unittest.TestCase):
    def test_bad_signature_and_expiration(self):
        username, token = login()
        claims = jwt.decode(token, KEY, algorithms=["HS256"], audience=AUDIENCE)
        forged = jwt.encode(claims, b"x" * 32, algorithm="HS256")
        now = datetime.now(timezone.utc)
        expired = jwt.encode({
            "sub": username, "aud": AUDIENCE, "iss": ISSUER, "amr": ["pwd", "otp"],
            "iat": now - timedelta(minutes=20), "exp": now - timedelta(minutes=5),
        }, KEY, algorithm="HS256")
        for invalid in (forged, expired):
            self.assertEqual(request("GET", "/section-2/auth/me", token=invalid)[0], 401)
