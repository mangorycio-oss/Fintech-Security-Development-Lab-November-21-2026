import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GATEWAY_URL = os.getenv("TEST_GATEWAY_URL")


@unittest.skipUnless(GATEWAY_URL, "Set TEST_GATEWAY_URL to a dedicated gateway instance")
class GatewayTests(unittest.TestCase):
    def request(self, method, path, body=None):
        req = Request(GATEWAY_URL + path, method=method, data=body)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers

    def test_forwards_allowed_routes_and_keeps_security_headers(self):
        status, headers = self.request("GET", "/section-2/auth/me")
        self.assertEqual(status, 401)
        self.assertEqual(headers["WWW-Authenticate"], "Bearer")
        self.assertEqual(headers.get_all("Cache-Control"), ["no-store"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        request_id = headers["X-Request-ID"]
        self.assertRegex(request_id, r"^[0-9a-f]{32}$")

        status, headers = self.request("GET", "/section-2/webauthn/browser")
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertNotEqual(headers["X-Request-ID"], request_id)

        status, headers = self.request("GET", "/section-1/csrf/token")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_rejects_unknown_routes_and_methods(self):
        self.assertEqual(self.request("GET", "/section-2/unknown")[0], 404)
        for algorithm in ("rsa", "aes"):
            self.assertEqual(self.request("POST", f"/section-2/crypto/{algorithm}", b"{}")[0], 404)
        status, headers = self.request("GET", "/section-2/auth/login")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "POST")

    def test_rejects_oversize_request(self):
        status, headers = self.request("POST", "/section-2/auth/login", b"x" * (256 * 1024 + 1))
        self.assertEqual(status, 413)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_throttles_burst(self):
        with ThreadPoolExecutor(max_workers=24) as pool:
            statuses = list(pool.map(lambda _: self.request("GET", "/")[0], range(90)))
        self.assertIn(200, statuses)
        self.assertIn(429, statuses)
