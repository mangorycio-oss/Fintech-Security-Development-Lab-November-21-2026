import hashlib

from fastapi import HTTPException


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def require_grant(db, token, scope):
    if not token:
        raise HTTPException(401, "Bank access token required")
    grant = db.execute(
        "SELECT owner, scopes FROM grants WHERE token_hash = ?",
        (token_hash(token),),
    ).fetchone()
    if not grant:
        raise HTTPException(401, "Invalid bank access token")
    if scope not in grant["scopes"].split():
        raise HTTPException(403, f"Bank consent required for {scope}")
    return grant["owner"]
