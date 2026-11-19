import os
import tempfile

from shared.database import sqlite_transaction

_direct = tempfile.TemporaryDirectory(prefix="fintech-lab-")
DATABASE = os.path.join(_direct.name, "lab.sqlite3")


def transaction():
    return sqlite_transaction(DATABASE)


def initialize():
    with transaction() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                name TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                totp_secret TEXT NOT NULL, last_step INTEGER NOT NULL DEFAULT -1
            );
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, purpose TEXT NOT NULL,
                payload TEXT NOT NULL, expires INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bank_tokens (
                owner TEXT PRIMARY KEY, token TEXT NOT NULL, scopes TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', receipt TEXT
            );
            CREATE TABLE IF NOT EXISTS rates (
                actor TEXT NOT NULL, action TEXT NOT NULL, window INTEGER NOT NULL,
                hits INTEGER NOT NULL, PRIMARY KEY(actor, action)
            );
        """)
