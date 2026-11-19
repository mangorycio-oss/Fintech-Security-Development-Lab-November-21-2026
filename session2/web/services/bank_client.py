import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException

from shared.bank_identity import KEY_PATH
from shared.bank_protocol import CLIENT_ID, REDIRECT_URI


def call(method, path, authorization, data=None, content_type="application/json"):
    base_url = os.getenv("BANK_API_URL", "http://127.0.0.1:8001")
    request = Request(
        base_url + path, method=method,
        headers={"Authorization": authorization, "Content-Type": content_type},
        data=data,
    )
    try:
        with urlopen(request, timeout=3) as response:
            return json.load(response)
    except HTTPError as error:
        with error:
            if error.code in (400, 403, 409):
                raise HTTPException(error.code, json.load(error)["detail"]) from error
            if error.code == 401 and path != "/token":
                raise HTTPException(403, "Bank consent required") from error
        raise HTTPException(502, "Bank rejected the request") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise HTTPException(503, "Bank service unavailable") from error


def exchange_code(code, verifier):
    try:
        key = KEY_PATH.read_bytes().hex()
    except OSError as error:
        raise HTTPException(503, "Bank service unavailable") from error
    client = base64.b64encode(f"{CLIENT_ID}:{key}".encode()).decode()
    data = urlencode({"grant_type": "authorization_code", "code": code,
                      "code_verifier": verifier, "redirect_uri": REDIRECT_URI}).encode()
    return call("POST", "/token", f"Basic {client}", data, "application/x-www-form-urlencoded")


def bank_token(db, owner, scope):
    row = db.execute("SELECT token FROM bank_tokens WHERE owner = ?", (owner,)).fetchone()
    if not row:
        raise HTTPException(403, f"Bank consent required for {scope}")
    return f'Bearer {row["token"]}'


def require_payment_scope(db, owner):
    call("GET", "/payments/scope", bank_token(db, owner, "payments:write"))


def accounts(db, owner):
    return call("GET", "/accounts", bank_token(db, owner, "accounts:read"))


def settle_payment(db, owner, amount, payment_id):
    return call("POST", "/payments", bank_token(db, owner, "payments:write"),
                json.dumps({"payment_id": payment_id, "amount_krw": amount}).encode())
