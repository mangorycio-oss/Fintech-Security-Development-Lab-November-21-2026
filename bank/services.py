import secrets

from fastapi import HTTPException

from bank.database import transaction
from bank.security import require_grant


def settle_payment(token, payment_id, amount_krw):
    with transaction() as db:
        username = require_grant(db, token, "payments:write")
        row = db.execute("SELECT * FROM settlements WHERE payment_id = ?", (payment_id,)).fetchone()
        if row:
            if row["owner"] != username or row["amount"] != amount_krw:
                raise HTTPException(409, "Payment ID already used")
            reference = row["bank_reference"]
        else:
            reference = secrets.token_urlsafe(16)
            db.execute("INSERT INTO settlements VALUES (?, ?, ?, ?)",
                       (payment_id, username, amount_krw, reference))
    return {"bank_reference": reference, "amount_krw": amount_krw, "currency": "KRW"}
