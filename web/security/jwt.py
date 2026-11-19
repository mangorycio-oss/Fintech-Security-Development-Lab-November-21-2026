import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

KEY = secrets.token_bytes(32)
ISSUER = "fintech-security-lab"
AUDIENCE = "section2-api"
bearer = HTTPBearer(auto_error=False)


def issue_token(username):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": username, "iss": ISSUER, "aud": AUDIENCE, "iat": now,
         "exp": now + timedelta(minutes=15), "amr": ["pwd", "otp"]},
        KEY,
        algorithm="HS256",
    )


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials:
        try:
            claims = jwt.decode(
                credentials.credentials, KEY, algorithms=["HS256"], issuer=ISSUER,
                audience=AUDIENCE, options={"require": ["sub", "iat", "exp", "amr"]},
            )
            if claims["amr"] == ["pwd", "otp"]:
                return claims["sub"]
        except jwt.InvalidTokenError:
            pass
    raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
