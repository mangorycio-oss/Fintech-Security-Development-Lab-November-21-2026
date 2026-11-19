import sqlite3

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from web.database import transaction
from shared.challenges import consume_challenge, issue_challenge, read_challenge
from web.models import Account, MFARequest
from web.security.jwt import current_user, issue_token
from web.security.mfa import matching_step, new_secret
from web.security.password import DUMMY_HASH, hash_password, verify_password
from web.security.rate_limit import enforce_rate

router = APIRouter(prefix="/auth")


@router.post("/register", status_code=201)
def register(account: Account, request: Request, response: Response):
    enforce_rate(request.client.host, "register", 20, 60)
    secret = new_secret()
    # 비밀번호는 Argon2id 해시로 저장하고, 설정 URI는 가입 응답에서만 전달한다.
    encoded = hash_password(account.password)
    try:
        with transaction() as db:
            db.execute("INSERT INTO users(name,password_hash,totp_secret) VALUES (?,?,?)",
                       (account.username, encoded, secret))
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, "Account already exists") from error
    response.headers["Cache-Control"] = "no-store"
    return {"username": account.username, "stored_format": encoded.split("$")[1],
            "totp_setup_uri": pyotp.TOTP(secret).provisioning_uri(name=account.username, issuer_name="Fintech Lab")}


@router.post("/login")
def login(account: Account, request: Request):
    enforce_rate(request.client.host, "login", 30, 60)
    with transaction() as db:
        row = db.execute("SELECT password_hash FROM users WHERE name = ?", (account.username,)).fetchone()
    # 사용자 조회 결과가 없어도 더미 해시를 검증해 비밀번호 검사 시간을 비슷하게 유지한다.
    verified = verify_password(row["password_hash"] if row else DUMMY_HASH, account.password)
    if not row or not verified:
        raise HTTPException(401, "Incorrect credentials")
    with transaction() as db:
        # 비밀번호 확인 단계에서는 JWT 대신 짧은 수명의 MFA 챌린지를 발급한다.
        challenge = issue_challenge(db, account.username, "mfa", {})
    return {"mfa_required": True, "challenge": challenge}


@router.post("/mfa")
def verify_mfa(body: MFARequest, request: Request, response: Response):
    enforce_rate(request.client.host, "mfa", 30, 60)
    with transaction() as db:
        username, _ = read_challenge(db, body.challenge, "mfa")
        row = db.execute("SELECT totp_secret, last_step FROM users WHERE name = ?", (username,)).fetchone()
        step = matching_step(row["totp_secret"], body.code, row["last_step"])
        if step is None:
            raise HTTPException(401, "Incorrect or previously used TOTP code")
        # 동일한 TOTP 시간 구간의 재사용 방지와 챌린지 소모를 한 트랜잭션으로 처리한다.
        db.execute("UPDATE users SET last_step = ? WHERE name = ?", (step, username))
        consume_challenge(db, body.challenge)
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": issue_token(username), "token_type": "bearer"}


@router.get("/me")
def me(username: str = Depends(current_user)):
    # Bearer 토큰의 서명, 만료와 인증 수단은 current_user 의존성에서 검사한다.
    return {"username": username, "amr": ["pwd", "otp"]}
