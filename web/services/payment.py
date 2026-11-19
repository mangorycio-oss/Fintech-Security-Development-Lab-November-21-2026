import json

from fastapi import HTTPException

from web.security.aes import decrypt, encrypt
from web.services import bank_client


def owned_payment(db, owner, payment_id):
    row = db.execute("SELECT * FROM payments WHERE id = ? AND owner = ?", (payment_id, owner)).fetchone()
    if not row:
        raise HTTPException(404, "Payment not found")
    return row


def complete(db, owner, payment_id):
    row = owned_payment(db, owner, payment_id)
    if row["status"] != "pending":
        raise HTTPException(409, "Payment already completed")
    receipt = bank_client.settle_payment(db, owner, row["amount"], payment_id)
    encrypted = encrypt(json.dumps(receipt).encode(), payment_id.encode())
    db.execute("UPDATE payments SET status = 'completed', receipt = ? WHERE id = ?", (encrypted, payment_id))
    return {"id": payment_id, "status": "completed", "encrypted_receipt": encrypted}


def get_receipt(row):
    return json.loads(decrypt(row["receipt"], row["id"].encode()))
