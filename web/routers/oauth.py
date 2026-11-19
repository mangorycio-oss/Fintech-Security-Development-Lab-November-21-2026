import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from shared.bank_protocol import CLIENT_ID, REDIRECT_URI, SCOPES, pkce_challenge
from web.database import transaction
from shared.challenges import consume_challenge, issue_challenge, read_challenge
from web.security.jwt import current_user
from web.services import bank_client

router = APIRouter(prefix="/bank")
COOKIE = "web_bank_state"
COOKIE_PATH = "/section-2/bank/callback"
BANK_BROWSER_URL = os.getenv("BANK_BROWSER_URL", "http://localhost:8001").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_BROWSER_URL", "http://localhost:8501").rstrip("/")
BROWSER_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


@router.post("/connect")
def start(username: str = Depends(current_user)):
    with transaction() as db:
        ticket = issue_challenge(db, username, "bank_start", {}, ttl=120)
    return {"path": f"/section-2/bank/connect/{ticket}"}


@router.get("/connect/{ticket}")
def open_bank(ticket: str, request: Request):
    verifier = secrets.token_urlsafe(48)
    with transaction() as db:
        owner, _ = read_challenge(db, ticket, "bank_start")
        consume_challenge(db, ticket)
        state = issue_challenge(db, owner, "bank_callback", {"verifier": verifier}, ttl=420)
    params = urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code",
        "code_challenge": pkce_challenge(verifier), "code_challenge_method": "S256",
        "state": state, "scope": " ".join(sorted(SCOPES)),
    })
    response = RedirectResponse(f"{BANK_BROWSER_URL}/authorize?{params}", status_code=303,
                                headers=BROWSER_HEADERS)
    response.set_cookie(COOKIE, state, max_age=420, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https", path=COOKIE_PATH)
    return response


@router.get("/callback")
def callback(request: Request, state: str, code: str | None = None, error: str | None = None):
    if not state or not secrets.compare_digest(state.encode(), request.cookies.get(COOKIE, "").encode()):
        raise HTTPException(400, "Invalid authorization state")
    if (code is None) == (error is None):
        raise HTTPException(400, "Invalid authorization response")

    with transaction() as db:
        username, context = read_challenge(db, state, "bank_callback")
        if code is not None:
            grant = bank_client.exchange_code(code, context["verifier"])
            db.execute(
                """INSERT INTO bank_tokens(owner, token, scopes) VALUES (?, ?, ?)
                ON CONFLICT(owner) DO UPDATE SET token = excluded.token, scopes = excluded.scopes""",
                (username, grant["access_token"], grant["scope"]),
            )
        consume_challenge(db, state)
    outcome = "connected" if code is not None else "cancelled"
    response = RedirectResponse(f"{FRONTEND_URL}/section2?bank={outcome}", status_code=303,
                                headers=BROWSER_HEADERS)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    return response


@router.get("/status")
def status(username: str = Depends(current_user)):
    with transaction() as db:
        grant = db.execute("SELECT scopes FROM bank_tokens WHERE owner = ?", (username,)).fetchone()
    return {"connected": grant is not None, "scopes": grant["scopes"].split() if grant else []}


@router.get("/accounts")
def read_accounts(username: str = Depends(current_user)):
    with transaction() as db:
        return bank_client.accounts(db, username)
