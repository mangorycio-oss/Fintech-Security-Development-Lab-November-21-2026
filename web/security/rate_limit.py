import time

from fastapi import HTTPException

from web.database import transaction


def enforce_rate(actor, action, limit, seconds):
    now = int(time.time())
    window = now // seconds
    with transaction() as db:
        db.execute(
            """
            INSERT INTO rates VALUES (?, ?, ?, 1)
            ON CONFLICT(actor, action) DO UPDATE SET
                hits = CASE WHEN rates.window = excluded.window THEN rates.hits + 1 ELSE 1 END,
                window = excluded.window
            """,
            (actor, action, window),
        )
        hits = db.execute(
            "SELECT hits FROM rates WHERE actor = ? AND action = ?", (actor, action)
        ).fetchone()["hits"]
    if hits > limit:
        raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(seconds - now % seconds)})
