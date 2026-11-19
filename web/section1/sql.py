
import hashlib
import secrets
import sqlite3
from contextlib import closing

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sql", tags=["SQL Injection"])

ITERATIONS = 600_000

DEMO_USERS = [
    ("admin", "admin-secret", "admin"),
    ("minji", "minji1234", "user"),
]


class Login(BaseModel):
    name: str = Field(max_length=200)
    password: str = Field(max_length=256)


def create_database():
    db = sqlite3.connect(":memory:")

    db.execute("""
        CREATE TABLE users (
            name TEXT PRIMARY KEY,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL,
            role TEXT NOT NULL
        )
    """)

    for name, password, role in DEMO_USERS:
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            ITERATIONS,
        )

        db.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            (name, password_hash, salt, role),
        )

    return db



import sqlite3
from contextlib import closing

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sql", tags=["SQL Injection"])

DEMO_USERS = [
    ("admin", "admin-secret", "admin"),
    ("minji", "minji1234", "user"),
]


class Login(BaseModel):
    name: str = Field(max_length=200)
    password: str = Field(max_length=256)


def create_database():
    """실습 요청마다 동일한 가상 계정 DB 생성"""
    db = sqlite3.connect(":memory:")

    db.execute("""
        CREATE TABLE users (
            name TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    db.executemany(
        "INSERT INTO users (name, password, role) VALUES (?, ?, ?)",
        DEMO_USERS,
    )

    return db


# BEFORE: SQL Injection 취약
@router.post("/before", summary="SQL Injection - 관리자 로그인 우회")
def before_login(login: Login):
    # 사용자 입력을 SQL 문자열에 직접 삽입
    query = (
        f"SELECT name, role FROM users "
        f"WHERE name = '{login.name}' "
        f"AND password = '{login.password}'"
    )

    with closing(create_database()) as db:
        try:
            row = db.execute(query).fetchone()
        except sqlite3.Error as error:
            return {
                "authenticated": False,
                "name": None,
                "role": None,
                "query": query,
                "error": str(error),
            }

    return {
        "authenticated": row is not None,
        "name": row[0] if row else None,
        "role": row[1] if row else None,
        "query": query,
    }


# AFTER: SQL Injection 방어
# 로그인 검증은 바인딩한 이름으로 사용자 행을 찾은 뒤 수행한다.
@router.post("/after", summary="SQL Injection - 파라미터 바인딩")
def after_login(login: Login):
    query = (
        "SELECT name, role FROM users "
        "WHERE name = ? AND password = ?"
    )

    with closing(create_database()) as db:
        row = db.execute(
            query,
            (login.name, login.password),
        ).fetchone()

    return {
        "authenticated": row is not None,
        "name": row[0] if row else None,
        "role": row[1] if row else None,
    }
