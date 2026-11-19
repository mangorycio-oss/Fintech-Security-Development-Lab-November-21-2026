import json
import os
import unittest
from urllib.request import urlopen


class Session1Routes(unittest.TestCase):
    def test_routes_are_registered(self):
        api_url = os.getenv("SESSION1_API_URL", "http://localhost:8002")
        with urlopen(api_url + "/openapi.json", timeout=5) as response:
            paths = json.load(response)["paths"]
        for topic in ("sql", "xss", "csrf"):
            self.assertTrue(any(path.startswith(f"/section-1/{topic}/") for path in paths))
        self.assertFalse(any(path.startswith("/section-2/") for path in paths))
