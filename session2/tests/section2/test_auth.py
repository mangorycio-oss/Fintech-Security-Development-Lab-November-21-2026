import unittest

import pyotp

from web.database import transaction
from tests import register, request


class AuthTests(unittest.TestCase):
    def test_argon2_and_mfa(self):
        account, signup = register()
        self.assertEqual(signup["stored_format"], "argon2id")
        with transaction() as db:
            row = db.execute("SELECT password_hash FROM users WHERE name = ?", (account["username"],)).fetchone()
        self.assertTrue(row["password_hash"].startswith("$argon2id$"))
        status, _, step = request("POST", "/section-2/auth/login", account)
        self.assertEqual(status, 200)
        self.assertNotIn("access_token", step)
        self.assertEqual(request("GET", "/section-2/auth/me", token=step["challenge"])[0], 401)
        code = pyotp.parse_uri(signup["totp_setup_uri"]).now()
        wrong = f"{(int(code) + 1) % 1_000_000:06d}"
        body = {"challenge": step["challenge"], "code": wrong}
        self.assertEqual(request("POST", "/section-2/auth/mfa", body)[0], 401)
        body["code"] = code
        status, _, data = request("POST", "/section-2/auth/mfa", body)
        self.assertEqual(status, 200)
        self.assertEqual(request("GET", "/section-2/auth/me", token=data["access_token"])[0], 200)
        self.assertEqual(request("POST", "/section-2/auth/mfa", body)[0], 400)
