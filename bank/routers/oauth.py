import base64
import re
import secrets
from html import escape
from urllib.parse import parse_qs, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from bank.database import transaction
from bank.security import token_hash
from shared.bank_identity import KEY_PATH
from shared.bank_protocol import CLIENT_ID, PKCE_PATTERN, REDIRECT_URI, SCOPES, pkce_challenge
from shared.challenges import consume_challenge, issue_challenge, read_challenge

router = APIRouter()

BANK_BROWSER_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
}


async def read_form(request):
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
        raise HTTPException(400, "Invalid form")
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > 8192:
            raise HTTPException(413, "Form too large")
        payload.extend(chunk)
    try:
        return parse_qs(payload.decode(), keep_blank_values=True, max_num_fields=16)
    except ValueError as error:
        raise HTTPException(400, "Invalid form") from error


@router.get("/authorize", response_class=HTMLResponse)
def authorize(request: Request, client_id: str, redirect_uri: str, response_type: str,
              code_challenge: str, code_challenge_method: str, state: str, scope: str):
    if (client_id != CLIENT_ID or redirect_uri != REDIRECT_URI or response_type != "code"
            or code_challenge_method != "S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", code_challenge)
            or not re.fullmatch(PKCE_PATTERN, state) or set(scope.split()) != SCOPES):
        raise HTTPException(400, "Invalid authorization request")
    demo_session = request.cookies.get("bank_demo", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", demo_session):
        demo_session = secrets.token_urlsafe(32)
    with transaction() as db:
        flow = issue_challenge(db, token_hash(demo_session), "bank_consent",
                               {"state": state, "code_challenge": code_challenge}, ttl=300)
    response = HTMLResponse(f"""<!doctype html>
<html lang="ko"><meta charset="utf-8"><title>가상 은행 권한 동의</title>
<h1>가상 은행 연결</h1>
<p>실습 계좌에서 핀테크 웹에 허용할 기능을 선택하세요.</p>
<form method="post" action="/authorize">
<input type="hidden" name="flow" value="{escape(flow)}">
<p><label><input type="checkbox" name="scope" value="accounts:read" checked> 계좌 조회</label></p>
<p><label><input type="checkbox" name="scope" value="payments:write"> 결제 요청</label></p>
<button name="decision" value="allow">동의</button>
<button name="decision" value="deny">취소</button>
</form></html>""", headers=BANK_BROWSER_HEADERS)
    response.set_cookie("bank_demo", demo_session, max_age=30 * 24 * 60 * 60, httponly=True,
                        samesite="lax", secure=request.url.scheme == "https", path="/authorize")
    response.set_cookie("bank_consent", flow, max_age=300, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https", path="/authorize")
    return response


@router.post("/authorize")
async def decide(request: Request):
    form = await read_form(request)
    flow = form.get("flow", [""])[0]
    if not flow or not secrets.compare_digest(flow.encode(), request.cookies.get("bank_consent", "").encode()):
        raise HTTPException(400, "Invalid consent session")
    decision = form.get("decision", [""])[0]
    scopes = set(form.get("scope", []))
    if decision not in {"allow", "deny"} or not scopes <= SCOPES:
        raise HTTPException(400, "Invalid consent choice")
    with transaction() as db:
        owner, consent = read_challenge(db, flow, "bank_consent")
        consume_challenge(db, flow)
        result = {"state": consent["state"]}
        if decision == "allow" and scopes:
            result["code"] = issue_challenge(
                db, owner, "bank_code",
                {"code_challenge": consent["code_challenge"], "scopes": sorted(scopes)}, ttl=60,
            )
        else:
            result["error"] = "access_denied"
    response = RedirectResponse(f"{REDIRECT_URI}?{urlencode(result)}", status_code=303,
                                headers=BANK_BROWSER_HEADERS)
    response.delete_cookie("bank_consent", path="/authorize")
    return response


@router.post("/token")
async def exchange(request: Request):
    client = base64.b64encode(f"{CLIENT_ID}:{KEY_PATH.read_bytes().hex()}".encode()).decode()
    if not secrets.compare_digest(request.headers.get("Authorization", "").encode(), f"Basic {client}".encode()):
        raise HTTPException(401, "Invalid bank client")
    form = await read_form(request)
    code = form.get("code", [""])[0]
    verifier = form.get("code_verifier", [""])[0]
    if (form.get("grant_type") != ["authorization_code"] or form.get("redirect_uri") != [REDIRECT_URI]
            or not re.fullmatch(PKCE_PATTERN, verifier)):
        raise HTTPException(400, "Invalid token request")
    with transaction() as db:
        owner, consent = read_challenge(db, code, "bank_code")
        if not secrets.compare_digest(consent["code_challenge"], pkce_challenge(verifier)):
            raise HTTPException(400, "Invalid PKCE verifier")
        consume_challenge(db, code)
        token = secrets.token_urlsafe(32)
        scopes = consent["scopes"]
        db.execute("INSERT INTO grants VALUES (?, ?, ?)", (token_hash(token), owner, " ".join(scopes)))
    return JSONResponse({"access_token": token, "token_type": "Bearer", "scope": " ".join(scopes)},
                        headers={"Cache-Control": "no-store"})
