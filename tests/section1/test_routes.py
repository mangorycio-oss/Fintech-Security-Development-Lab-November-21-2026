import unittest

from tests import request


class Section1Routes(unittest.TestCase):
    def test_sections_are_registered(self):
        status, _, schema = request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        for topic in ("sql", "xss", "csrf"):
            self.assertTrue(any(path.startswith(f"/section-1/{topic}/") for path in schema["paths"]))
