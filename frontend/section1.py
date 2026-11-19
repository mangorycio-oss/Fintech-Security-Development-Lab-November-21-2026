import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/") + "/section-1"


def show_response(response, *, as_html_source=False):
    st.caption(f"HTTP {response.status_code}")
    if as_html_source and response.ok:
        st.code(response.text, language="html")
    else:
        st.json(response.json())


def compare(
    topic,
    method,
    *,
    show_after_as_html=False,
    preview_notice=None,
    animate_preview=False,
    **kwargs,
):
    before, after = st.columns(2)
    for column, stage, label in (
        (before, "before", "리팩토링 전"),
        (after, "after", "리팩토링 후"),
    ):
        with column:
            st.subheader(label)
            try:
                response = requests.request(
                    method, f"{API_URL}/{topic}/{stage}", timeout=5, **kwargs
                )
                if stage == "before" and response.ok and preview_notice:
                    preview = st.empty()
                    if animate_preview:
                        st.caption("JavaScript 실행 화면 모의 연출")
                        for _ in range(2):
                            preview.error("당신은 해킹당했습니다.")
                            time.sleep(0.7)
                            preview.warning("입력된 JavaScript가 실행되고 있습니다.")
                            time.sleep(0.7)
                        preview.error("당신은 해킹당했습니다.")
                    else:
                        preview.error(preview_notice)
                show_response(response, as_html_source=show_after_as_html and stage == "after")
                if topic == "xss" and stage == "after" and response.ok:
                    st.text(kwargs["json"]["text"])
            except (requests.RequestException, ValueError):
                st.error("FastAPI 응답을 읽을 수 없습니다.")


st.title("Section 1 · 시큐어 코딩 실습")
sql_tab, xss_tab, csrf_tab = st.tabs(["SQL Injection", "XSS", "CSRF"])


with sql_tab:
    st.markdown(
        "가상 은행의 관리자 계정(admin)에 로그인하는 상황입니다. "
        "공격자는 관리자 비밀번호를 모르지만, "
        "아이디 입력란에 SQL 문법을 삽입해 인증을 우회하려고 합니다."
    )

    st.info(
        "실습 목표: 취약한 SQL에서는 관리자 계정으로 로그인되지만, "
        "파라미터 바인딩을 사용한 SQL에서는 로그인이 거절되는지 확인합니다."
    )

    samples = {
        "관리자 로그인 우회": {
            "name": "admin' -- ",
            "password": "wrong",
        },
        "항상 참인 조건": {
            "name": "' OR '1'='1' -- ",
            "password": "wrong",
        },
        "정상 관리자 로그인": {
            "name": "admin",
            "password": "admin-secret",
        },
        "틀린 비밀번호": {
            "name": "admin",
            "password": "wrong",
        },
    }

    selected = st.selectbox(
        "SQL Injection 테스트 시나리오",
        options=list(samples.keys()),
    )

    sample = samples[selected]

    with st.form("sql"):
        name = st.text_input(
            "아이디",
            value=sample["name"],
        )

        password = st.text_input(
            "비밀번호",
            value=sample["password"],
            type="password",
        )

        run_sql = st.form_submit_button(
            "로그인 결과 비교",
            use_container_width=True,
        )

    if run_sql:
        payload = {
            "name": name,
            "password": password,
        }

        before_col, after_col = st.columns(2)

        for column, stage, title in (
            (before_col, "before", "리팩토링 전 · 취약한 로그인"),
            (after_col, "after", "리팩토링 후 · 안전한 로그인"),
        ):
            with column:
                st.subheader(title)

                try:
                    response = requests.post(
                        f"{API_URL}/sql/{stage}",
                        json=payload,
                        timeout=10,
                    )
                    response.raise_for_status()
                    result = response.json()

                    if result.get("authenticated"):
                        role = result.get("role")
                        username = result.get("name")

                        if role == "admin":
                            if stage == "before" and selected != "정상 관리자 로그인":
                                st.error("관리자 로그인 우회 성공!")
                            else:
                                st.success("관리자 로그인 성공")
                        else:
                            st.warning("일반 사용자로 로그인되었습니다.")

                        st.write(f"로그인 계정: {username}")
                        st.write(f"권한: {role}")

                    else:
                        if stage == "after":
                            st.success("인증되지 않은 요청이 거절되었습니다.")
                        else:
                            st.info("로그인에 실패했습니다.")

                    if result.get("error"):
                        st.error(f"SQL 오류: {result['error']}")

                    if stage == "before" and result.get("query"):
                        with st.expander("실제로 실행된 SQL 확인", expanded=True):
                            st.code(result["query"], language="sql")

                    with st.expander("API 응답 JSON"):
                        st.json(result)

                except requests.HTTPError:
                    st.error(
                        f"API 오류: HTTP {response.status_code}"
                    )
                except (requests.RequestException, ValueError, KeyError):
                    st.error("FastAPI 응답을 읽을 수 없습니다.")


with xss_tab:
    st.markdown(
        "은행 상담 게시판에 누군가 댓글처럼 보이는 HTML이나 JavaScript를 올렸습니다. "
        "다른 고객이 글을 열었을 때 게시판에 어떤 문구가 보이는지 비교해 보세요."
    )
    samples = {
        "화면 문구 변조 · HTML": "<h1>당신은 해킹당했습니다!</h1>",
        "화면 제목 변조 · JavaScript": 'document.title = "당신은 해킹당했습니다!";',
    }
    sample = st.selectbox("입력 예시", list(samples))
    with st.form("xss"):
        message = st.text_area("메시지", value=samples[sample], key=f"xss_{sample}")
        run_xss = st.form_submit_button("고객이 게시글을 열었을 때 비교")
    if run_xss:
        compare(
            "xss",
            "POST",
            show_after_as_html=True,
            animate_preview=message == samples["화면 제목 변조 · JavaScript"],
            json={"text": message},
            preview_notice=(
                "화면 변조 모의 결과 · 당신은 해킹당했습니다!"
                if message in samples.values() else None
            ),
        )

with csrf_tab:
    st.markdown(
        "인터넷뱅킹에 로그인한 채 같은 브라우저에서 할인 쿠폰 사이트를 열었습니다. "
        "외부 사이트가 내 동의 없이 은행에 **100만 원 송금 요청**을 보낸 상황입니다."
    )
    st.caption("교차 사이트 요청을 모의합니다. SameSite가 차단한 쿠키는 요청에서 생략합니다.")
    if st.button("외부 사이트의 송금 요청 비교"):
        body = {"amount_krw": 1_000_000, "recipient": "외부 실습 계좌"}
        headers = {"Origin": "https://other.example"}
        try:
            st.subheader("리팩토링 전")
            response = requests.post(f"{API_URL}/csrf/before", json=body, headers=headers, timeout=5)
            response.raise_for_status()
            loss = response.json()["simulated_loss_krw"]
            st.error(f"모의 결과 · {loss:,}원이 털렸습니다.")
            show_response(response)

            defenses = (
                ("samesite", "SameSite", "교차 사이트 요청에 은행 세션 쿠키가 빠져 송금이 거절됐습니다."),
                ("origin", "Origin / Referer", "요청 출처가 은행과 달라 송금이 거절됐습니다."),
                ("token", "CSRF 토큰", "외부 사이트 요청에 유효한 토큰이 없어 송금이 거절됐습니다."),
            )
            for column, (route, label, reason) in zip(st.columns(3), defenses):
                with column:
                    st.subheader(label)
                    response = requests.post(
                        f"{API_URL}/csrf/after/{route}", json=body, headers=headers, timeout=5
                    )
                    if response.status_code == 403:
                        st.success(reason)
                    else:
                        st.warning("예상한 거절 응답이 돌아오지 않았습니다.")
                    show_response(response)
        except (requests.RequestException, ValueError, KeyError):
            st.error("FastAPI 응답을 읽을 수 없습니다.")
