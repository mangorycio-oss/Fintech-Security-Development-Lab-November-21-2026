import os
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel

router = APIRouter(prefix="/csrf")
trusted_origin = os.getenv("CSRF_TRUSTED_ORIGIN", "http://localhost:8000")
cookie_name = "section1_csrf"
samesite_cookie_name = "section1_samesite"


class Transfer(BaseModel):
    amount_krw: int
    recipient: str


@router.post("/before", summary="CSRF · 검증 누락 시 처리 흐름 미리보기")
def preview_transfer(transfer: Transfer):
    # 피해 금액은 실습용 계산값이다. 실제 송금 상태는 변경하지 않는다.
    return {
        "requested_transfer": transfer,
        "checks": {"token": False, "same_site": False, "origin_or_referer": False},
        "simulated_loss_krw": transfer.amount_krw,
        "applied": False,
    }


@router.get("/samesite/session", summary="CSRF · SameSite 실습 쿠키 발급")
def issue_samesite_session(response: Response):
    response.set_cookie(
        samesite_cookie_name,
        "demo",
        httponly=True,
        secure=trusted_origin.startswith("https://"),
        samesite="strict",
        path="/section-1/csrf/after/samesite",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"same_site": "strict"}


@router.post("/after/samesite", summary="CSRF 개선 1 · SameSite 쿠키")
def check_samesite(transfer: Transfer, request: Request):
    # 쿠키 전송 여부는 브라우저가 결정하며, 서버는 쿠키가 도착했는지 확인한다.
    if request.cookies.get(samesite_cookie_name) != "demo":
        raise HTTPException(403, "SameSite demo cookie missing")
    return {"validated": True, "requested_transfer": transfer}


@router.get("/token", summary="CSRF · 토큰 발급")
def issue_token(response: Response):
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=trusted_origin.startswith("https://"),
        samesite="strict",
        path="/section-1/csrf",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


@router.post("/after/origin", summary="CSRF 개선 2 · Origin 및 Referer 검증")
def check_origin(transfer: Transfer, request: Request):
    # Origin을 우선하며, 헤더 자체가 없을 때만 Referer의 출처로 대체한다.
    origin = request.headers.get("origin")
    if origin is None:
        try:
            referer = urlsplit(request.headers.get("referer", ""))
            if referer.username is None and referer.password is None:
                origin = f"{referer.scheme}://{referer.netloc}"
        except ValueError:
            pass
    if origin != trusted_origin:
        raise HTTPException(403, "Untrusted request origin")
    return {"validated": True, "requested_transfer": transfer}


@router.post("/after/token", summary="CSRF 개선 3 · CSRF 토큰 검증")
def check_token(
    transfer: Transfer, request: Request, x_csrf_token: str = Header(default="")
):
    # 쿠키와 요청 헤더에 들어온 토큰이 모두 필요하다.
    cookie = request.cookies.get(cookie_name, "")
    if not cookie or not x_csrf_token or not secrets.compare_digest(
        cookie.encode(), x_csrf_token.encode()
    ):
        raise HTTPException(403, "Invalid CSRF token")
    return {"validated": True, "requested_transfer": transfer}
