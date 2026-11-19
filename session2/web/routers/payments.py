import secrets

from fastapi import APIRouter, Depends, HTTPException

from web.database import transaction
from shared.payment import PaymentRequest
from web.security.jwt import current_user
from web.security.rate_limit import enforce_rate
from web.services import bank_client, payment

router = APIRouter(prefix="/payments")


@router.post("", status_code=201)
def create(body: PaymentRequest, username: str = Depends(current_user)):
    # 검증된 사용자별로 60초 고정 구간에 결제 요청을 세 건까지 받는다.
    enforce_rate(username, "payments", 3, 60)
    identifier = secrets.token_urlsafe(16)
    with transaction() as db:
        bank_client.require_payment_scope(db, username)
        # 이 단계에서는 요청만 만들고, 은행 처리는 패스키 승인 뒤에 진행한다.
        db.execute("INSERT INTO payments(id, owner, amount) VALUES (?, ?, ?)",
                   (identifier, username, body.amount_krw))
    return {"id": identifier, "amount_krw": body.amount_krw, "status": "pending"}


@router.get("/{payment_id}")
def status(payment_id: str, username: str = Depends(current_user)):
    # 결제 ID를 알고 있어도 요청자가 소유한 결제만 조회할 수 있다.
    with transaction() as db:
        row = payment.owned_payment(db, username, payment_id)
        return {"id": row["id"], "amount_krw": row["amount"], "status": row["status"],
                "encrypted_receipt": row["receipt"]}


@router.get("/{payment_id}/receipt")
def receipt(payment_id: str, username: str = Depends(current_user)):
    with transaction() as db:
        row = payment.owned_payment(db, username, payment_id)
        if row["status"] != "completed":
            raise HTTPException(409, "Payment is pending approval")
        # 소유권과 완료 상태를 검증한 다음 저장된 영수증을 복호화한다.
        return payment.get_receipt(row)
