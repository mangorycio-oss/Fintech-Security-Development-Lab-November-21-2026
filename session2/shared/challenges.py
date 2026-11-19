import json
import secrets
import time

from fastapi import HTTPException


def issue_challenge(db, owner, purpose, payload, ttl=180):
    now = int(time.time())
    db.execute("DELETE FROM challenges WHERE expires <= ?", (now,))
    identifier = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO challenges VALUES (?, ?, ?, ?, ?)",
        (identifier, owner, purpose, json.dumps(payload), now + ttl),
    )
    return identifier


def read_challenge(db, identifier, purpose, owner=None):
    row = db.execute(
        "SELECT * FROM challenges WHERE id = ? AND purpose = ? AND expires > ?",
        (identifier, purpose, int(time.time())),
    ).fetchone()
    if not row or (owner is not None and row["owner"] != owner):
        raise HTTPException(400, "Invalid or expired challenge")
    return row["owner"], json.loads(row["payload"])


def consume_challenge(db, identifier):
    db.execute("DELETE FROM challenges WHERE id = ?", (identifier,))
