from html import escape

from fastapi import APIRouter, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/xss")


class Message(BaseModel):
    text: str


sample = Body(
    openapi_examples={
        "javascript": {
            "summary": "HTML에 포함될 수 있는 JavaScript 예시",
            "value": {"text": "console.log('Section 1')"},
        },
        "markup": {
            "summary": "HTML 출력 인코딩 확인",
            "value": {"text": "<strong>결제 완료</strong> & 확인"},
        },
    }
)


@router.post("/before", summary="XSS · 인코딩 전 HTML 소스 미리보기")
def preview_message(message: Message = sample):
    # 원본 HTML은 JSON 문자열로 반환해 출력 인코딩 전 소스를 비교한다.
    return {"html_source": f"<p>{message.text}</p>"}


@router.post("/after", response_class=HTMLResponse, summary="XSS · HTML 출력 인코딩")
def render_message(message: Message = sample):
    # HTML 본문에 넣을 사용자 문자열을 이 위치의 문맥에 맞게 이스케이프한다.
    return f"<p>{escape(message.text)}</p>"
