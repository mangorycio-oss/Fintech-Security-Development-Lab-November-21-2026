from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from bank.database import transaction
from bank import services
from bank.security import require_grant
from shared.payment import PaymentRequest

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def access_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    return credentials.credentials if credentials else None


@router.get("/accounts")
def accounts(token: str | None = Depends(access_token)):
    with transaction() as db:
        username = require_grant(db, token, "accounts:read")
    return {"accounts": [{"id": f"lab-{username}", "currency": "KRW"}]}


@router.get("/payments/scope")
def payment_scope(token: str | None = Depends(access_token)):
    with transaction() as db:
        require_grant(db, token, "payments:write")
    return {"allowed": True}


class Settlement(PaymentRequest):
    payment_id: str = Field(min_length=1, max_length=100)


@router.post("/payments")
def settle_payment(body: Settlement, token: str | None = Depends(access_token)):
    return services.settle_payment(token, body.payment_id, body.amount_krw)
