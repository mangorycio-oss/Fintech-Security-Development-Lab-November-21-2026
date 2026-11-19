import json
import os
import secrets
import socket
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pyotp
import uvicorn

_bank_dir = tempfile.TemporaryDirectory(prefix="fintech-bank-test-")
os.environ["BANK_KEY_PATH"] = os.path.join(_bank_dir.name, "key")
os.environ["BANK_DATABASE"] = os.path.join(_bank_dir.name, "bank.sqlite3")

from web.main import app
from web.routers import oauth
from bank.main import app as bank_app

BASE_URL = None
PASSWORD = "lab-only-password"


def start_server(application):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            return f"http://127.0.0.1:{port}"
        time.sleep(0.025)
    raise RuntimeError("Lab service failed to start")


def request(method, path, body=None, token=None):
    global BASE_URL
    if BASE_URL is None:
        os.environ["BANK_API_URL"] = start_server(bank_app)
        oauth.BANK_BROWSER_URL = os.environ["BANK_API_URL"]
        BASE_URL = start_server(app)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(BASE_URL + path, method=method, headers=headers,
                  data=json.dumps(body).encode() if body is not None else None)
    try:
        response = urlopen(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        payload = response.read().decode()
        if "application/json" in response.headers.get("Content-Type", ""):
            payload = json.loads(payload)
        return response.status, response.headers, payload


def register():
    account = {"username": "student-" + secrets.token_hex(5), "password": PASSWORD}
    status, _, data = request("POST", "/section-2/auth/register", account)
    assert status == 201, data
    return account, data


def login():
    account, data = register()
    status, _, step = request("POST", "/section-2/auth/login", account)
    assert status == 200, step
    status, _, result = request("POST", "/section-2/auth/mfa", {
        "challenge": step["challenge"],
        "code": pyotp.parse_uri(data["totp_setup_uri"]).now(),
    })
    assert status == 200, result
    return account["username"], result["access_token"]
