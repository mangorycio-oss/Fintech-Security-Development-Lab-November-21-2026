import os

from shared.database import sqlite_transaction

DATABASE = os.getenv("BANK_DATABASE", "/tmp/fintech-bank.sqlite3")


def transaction():
    return sqlite_transaction(DATABASE)


def initialize():
    with transaction() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS challenges (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, purpose TEXT NOT NULL,
                payload TEXT NOT NULL, expires INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS grants (
                token_hash TEXT PRIMARY KEY, owner TEXT NOT NULL, scopes TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settlements (
                payment_id TEXT PRIMARY KEY, owner TEXT NOT NULL, amount INTEGER NOT NULL,
                bank_reference TEXT NOT NULL
            );
        """)
