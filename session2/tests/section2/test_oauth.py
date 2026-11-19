import re
import secrets
import unittest
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

import tests
from web.services.bank_client import exchange_code
from fastapi import HTTPException
from tests import login, request


class StopRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def browser_request(browser, url, form=None):
    req = Request(url, data=urlencode(form, doseq=True).encode() if form else None)
    try:
        response = browser.open(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read().decode()


def bank_consent(token, scopes, decision="allow"):
    status, _, start = request("POST", "/section-2/bank/connect", {}, token)
    assert status == 200, start
    browser = build_opener(HTTPCookieProcessor(CookieJar()), StopRedirects())
    ticket_url = tests.BASE_URL + start["path"]
    status, headers, _ = browser_request(browser, ticket_url)
    assert status == 303
    assert browser_request(browser, ticket_url)[0] == 400
    consent_url = headers["Location"]
    status, _, html = browser_request(browser, consent_url)
    assert status == 200
    flow = re.search(r'name="flow" value="([^"]+)"', html)[1]
    bank_form = consent_url.split("?", 1)[0]
    status, headers, _ = browser_request(browser, bank_form, {
        "flow": flow, "scope": scopes, "decision": decision,
    })
    assert status == 303
    result = urlsplit(headers["Location"])
    return browser, tests.BASE_URL + result.path + "?" + result.query


def connect_bank(token, scopes):
    browser, callback = bank_consent(token, scopes)
    status, _, _ = browser_request(browser, callback)
    assert status == 303


class OAuthTests(unittest.TestCase):
    def test_pkce_state_replay_and_scope(self):
        _, token = login()
        browser, callback = bank_consent(token, ["accounts:read"])
        parts = urlsplit(callback)
        params = parse_qs(parts.query)
        with self.assertRaises(HTTPException) as error:
            exchange_code(params["code"][0], secrets.token_urlsafe(48))
        self.assertEqual(error.exception.status_code, 400)
        wrong_state = {**params, "state": [secrets.token_urlsafe(32)]}
        self.assertEqual(browser_request(browser, callback.split("?")[0] + "?" + urlencode(wrong_state, doseq=True))[0], 400)
        self.assertEqual(browser_request(build_opener(StopRedirects()), callback)[0], 400)
        self.assertEqual(browser_request(browser, callback)[0], 303)
        self.assertEqual(browser_request(browser, callback)[0], 400)
        self.assertEqual(request("GET", "/section-2/bank/status", token=token)[2], {
            "connected": True, "scopes": ["accounts:read"],
        })
        self.assertEqual(request("GET", "/section-2/bank/accounts", token=token)[0], 200)
        self.assertEqual(request("POST", "/section-2/payments", {"amount_krw": 1000}, token)[0], 403)

    def test_cancel_leaves_bank_disconnected(self):
        _, token = login()
        browser, callback = bank_consent(token, ["accounts:read"], decision="deny")
        status, headers, _ = browser_request(browser, callback)
        self.assertEqual(status, 303)
        self.assertTrue(headers["Location"].endswith("?bank=cancelled"))
        self.assertFalse(request("GET", "/section-2/bank/status", token=token)[2]["connected"])
