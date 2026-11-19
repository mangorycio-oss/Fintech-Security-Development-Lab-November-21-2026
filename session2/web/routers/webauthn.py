import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from webauthn import (
    base64url_to_bytes, generate_authentication_options, generate_registration_options,
    options_to_json, verify_authentication_response, verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor, UserVerificationRequirement,
)

from web.database import transaction
from shared.challenges import consume_challenge, issue_challenge, read_challenge
from web.security.jwt import current_user
from web.services import bank_client, payment

router = APIRouter(prefix="/webauthn")
ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:8000")
RP_ID = urlsplit(ORIGIN).hostname
UV = UserVerificationRequirement.REQUIRED
REGISTRATION_ALGORITHMS = [COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256]


class CredentialResponse(BaseModel):
    challenge_id: str = Field(max_length=100)
    credential: dict


def store_options(db, username, purpose, options, **context):
    # 브라우저에 보낸 챌린지를 사용자, 목적, 실습 데이터와 함께 서버에 저장한다.
    encoded = json.loads(options_to_json(options))
    identifier = issue_challenge(db, username, purpose, {"challenge": encoded["challenge"], **context})
    return {"challenge_id": identifier, "publicKey": encoded}


@router.get("/browser", response_class=HTMLResponse, include_in_schema=False)
def browser():
    # 패스키 요청을 API와 같은 출처의 브라우저 페이지에서 실행한다.
    return HTMLResponse(
        Path(__file__).with_name("webauthn.html").read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"},
    )


@router.post("/register/options")
def register_options(username: str = Depends(current_user)):
    with transaction() as db:
        existing = db.execute("SELECT id FROM credentials WHERE owner = ?", (username,))
        # 이미 등록된 자격 증명은 제외하고 인증기의 사용자 검증을 요구한다.
        options = generate_registration_options(
            rp_id=RP_ID, rp_name="Fintech Lab", user_name=username, user_id=username.encode(),
            authenticator_selection=AuthenticatorSelectionCriteria(user_verification=UV),
            supported_pub_key_algs=REGISTRATION_ALGORITHMS,
            exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(row["id"])) for row in existing],
        )
        return store_options(db, username, "passkey_register", options)


@router.post("/register/verify")
def register_verify(body: CredentialResponse, username: str = Depends(current_user)):
    with transaction() as db:
        _, context = read_challenge(db, body.challenge_id, "passkey_register", username)
        try:
            # 등록 챌린지, 출처, RP ID를 확인한 응답에서 공개키를 추출한다.
            credential = verify_registration_response(
                credential=body.credential, expected_challenge=base64url_to_bytes(context["challenge"]),
                expected_rp_id=RP_ID, expected_origin=ORIGIN, require_user_verification=True,
                supported_pub_key_algs=REGISTRATION_ALGORITHMS,
            )
            db.execute("INSERT INTO credentials VALUES (?, ?, ?, ?)",
                       (bytes_to_base64url(credential.credential_id), username,
                        credential.credential_public_key, credential.sign_count))
        except (InvalidRegistrationResponse, ValueError) as error:
            raise HTTPException(400, "Passkey registration could not be verified") from error
        except sqlite3.IntegrityError as error:
            raise HTTPException(409, "Passkey already registered") from error
        consume_challenge(db, body.challenge_id)
    return {"registered": True}


@router.post("/approve/{payment_id}/options")
def approve_options(payment_id: str, username: str = Depends(current_user)):
    with transaction() as db:
        row = payment.owned_payment(db, username, payment_id)
        bank_client.require_payment_scope(db, username)
        if row["status"] != "pending":
            raise HTTPException(409, "Payment already completed")
        credentials = db.execute("SELECT id FROM credentials WHERE owner = ?", (username,)).fetchall()
        if not credentials:
            raise HTTPException(409, "Register a passkey first")
        # 이 결제의 소유자가 등록한 패스키로만 승인 챌린지에 응답할 수 있다.
        options = generate_authentication_options(
            rp_id=RP_ID, user_verification=UV,
            allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(item["id"])) for item in credentials],
        )
        return {
            **store_options(db, username, "payment_approve", options, payment=payment_id),
            "payment": {"id": payment_id, "amount_krw": row["amount"]},
        }


@router.post("/approve/verify")
def approve_verify(body: CredentialResponse, username: str = Depends(current_user)):
    with transaction() as db:
        _, context = read_challenge(db, body.challenge_id, "payment_approve", username)
        credential_id = body.credential.get("id")
        if not isinstance(credential_id, str):
            raise HTTPException(400, "Invalid passkey ID")
        saved = db.execute("SELECT * FROM credentials WHERE id = ? AND owner = ?",
                           (credential_id, username)).fetchone()
        if not saved:
            raise HTTPException(400, "Unknown passkey")
        try:
            # 등록해 둔 공개키로 응답 서명과 인증기의 사용자 검증 결과를 확인한다.
            verified = verify_authentication_response(
                credential=body.credential, expected_challenge=base64url_to_bytes(context["challenge"]),
                expected_rp_id=RP_ID, expected_origin=ORIGIN, credential_public_key=saved["public_key"],
                credential_current_sign_count=saved["sign_count"], require_user_verification=True,
            )
        except (InvalidAuthenticationResponse, ValueError) as error:
            raise HTTPException(400, "Payment signature could not be verified") from error
        # 서명 카운터 갱신, 챌린지 소모, 결제 완료를 한 트랜잭션에 묶는다.
        db.execute("UPDATE credentials SET sign_count = ? WHERE id = ?", (verified.new_sign_count, saved["id"]))
        consume_challenge(db, body.challenge_id)
        return payment.complete(db, username, context["payment"])
