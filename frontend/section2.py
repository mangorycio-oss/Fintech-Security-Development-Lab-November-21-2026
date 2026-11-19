import os
import time
from urllib.parse import parse_qs, urlsplit

import pyotp
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000").rstrip("/") + "/section-2"
BROWSER_API = os.getenv("BROWSER_API_URL", "http://localhost:8000").rstrip("/")
state = st.session_state


def call(method, path, body=None, *, protected=False):
    headers = {}
    if protected:
        headers["Authorization"] = f"Bearer {state.get('access_token', '')}"
    try:
        response = requests.request(method, API + path, json=body, headers=headers, timeout=8)
        data = response.json()
    except (requests.RequestException, ValueError):
        st.error("API 응답을 읽을 수 없습니다.")
        return None
    if not response.ok:
        st.error(f"HTTP {response.status_code} · {data.get('detail', '요청 거부')}")
        return None
    return data


st.title("Section 2 · 핀테크 인증과 결제")
st.caption("가상 은행에서 계좌를 연결하고, 패스키로 승인한 결제의 암호화 영수증을 확인합니다.")
outcome = st.query_params.get("bank")
if outcome == "connected":
    st.success("은행 연결을 완료했습니다. 기존 탭의 ‘연결 상태 확인’을 누르세요.")
elif outcome == "cancelled":
    st.info("은행 연결을 취소했습니다.")

auth, authenticator, bank, pay = st.tabs([
    "① 가입 · ② 로그인", "TOTP 인증기", "③ 계좌 연결",
    "④ 결제 · ⑤ 승인 · ⑥ 완료",
])

with auth:
    st.subheader("회원가입과 Argon2id")
    with st.form("section2_register"):
        name = st.text_input("사용자 이름", help="영문, 숫자, 점, 밑줄, 하이픈 3~40자")
        password = st.text_input("새 비밀번호", type="password", help="12자 이상")
        register = st.form_submit_button("회원가입")
    if register:
        state.pop("totp_setup_uri", None)
        data = call("POST", "/auth/register", {"username": name, "password": password})
        if data:
            st.success(f"DB에 저장된 비밀번호 형식 · {data['stored_format']}")
            state["totp_setup_uri"] = data["totp_setup_uri"]
    if state.get("totp_setup_uri"):
        secret = parse_qs(urlsplit(state["totp_setup_uri"]).query)["secret"][0]
        st.caption("이 실습 계정의 설정 키를 복사해 ‘TOTP 인증기’ 탭에 붙여넣으세요.")
        st.code(secret, language="text")
        if st.button("설정 키 숨기기"):
            del state["totp_setup_uri"]
            st.rerun()

    st.subheader("비밀번호 → TOTP → JWT")
    with st.form("section2_login"):
        login_name = st.text_input("로그인 이름")
        login_password = st.text_input("로그인 비밀번호", type="password")
        login = st.form_submit_button("비밀번호 확인")
    if login:
        for key in ("mfa_challenge", "access_token", "payment_id", "bank_connect_path"):
            state.pop(key, None)
        data = call("POST", "/auth/login", {"username": login_name, "password": login_password})
        if data:
            state["mfa_challenge"] = data["challenge"]
    if state.get("mfa_challenge"):
        st.info("비밀번호 확인 완료. TOTP 검증 후에 JWT가 발급됩니다.")
        with st.form("section2_mfa"):
            code = st.text_input("TOTP 인증기의 6자리 코드", max_chars=6, autocomplete="one-time-code")
            verify = st.form_submit_button("TOTP 확인 및 JWT 발급")
        if verify:
            data = call("POST", "/auth/mfa", {"challenge": state["mfa_challenge"], "code": code})
            if data:
                state.pop("bank_connect_path", None)
                state["access_token"] = data["access_token"]
                del state["mfa_challenge"]
                st.rerun()
    if state.get("access_token"):
        st.success("MFA 완료 · 서명된 JWT 발급")
        if st.button("서명과 만료 검증"):
            data = call("GET", "/auth/me", protected=True)
            if data:
                st.json(data)

with authenticator:
    st.subheader("실습용 TOTP 인증기")
    st.caption("회원가입에서 받은 설정 키를 입력하고, 생성된 6자리 코드를 로그인 탭에 옮겨 적으세요.")
    st.info("같은 Streamlit 세션에서 코드를 생성하는 실습입니다. 별도 기기를 사용하는 운영 환경의 MFA와는 보안 수준이 다릅니다.")
    setup_key = st.text_input("TOTP 설정 키", type="password", max_chars=128)
    if setup_key.strip():
        @st.fragment(run_every=1)
        def show_totp():
            try:
                totp = pyotp.TOTP("".join(setup_key.split()).upper())
                now = int(time.time())
                code = totp.at(now)
            except ValueError:
                st.error("설정 키 형식을 확인하고 다시 붙여넣으세요.")
                return
            st.code(code, language="text")
            st.caption(f"새 코드까지 {totp.interval - now % totp.interval}초")

        show_totp()

with bank:
    st.subheader("실습 은행 연결")
    st.caption("은행 화면에서 계좌 조회와 결제 요청 중 허용할 권한을 선택하세요.")
    if st.button("연결 링크 만들기", disabled=not state.get("access_token")):
        result = call("POST", "/bank/connect", protected=True)
        state["bank_connect_path"] = result["path"] if result else None
    if state.get("access_token") and state.get("bank_connect_path"):
        st.link_button("은행 동의 화면 열기", BROWSER_API + state["bank_connect_path"])
    if st.button("연결 상태 확인", disabled=not state.get("access_token")):
        result = call("GET", "/bank/status", protected=True)
        if result:
            if result["connected"]:
                labels = {"accounts:read": "계좌 조회", "payments:write": "결제 요청"}
                st.success("동의한 권한 · " + ", ".join(labels[scope] for scope in result["scopes"]))
            else:
                st.info("연결된 은행 권한이 없습니다.")
    if st.button("은행 계좌 조회", disabled=not state.get("access_token")):
        data = call("GET", "/bank/accounts", protected=True)
        if data:
            st.json(data)

with pay:
    st.subheader("결제 요청")
    st.caption("결제 요청은 계좌 연결 시 결제 권한에 동의해야 합니다. 동일 계정은 분당 3회까지 요청할 수 있습니다.")
    with st.form("section2_payment"):
        amount = st.number_input("결제 금액 (원)", min_value=1, max_value=10_000_000, value=1000)
        create = st.form_submit_button("결제 요청", disabled=not state.get("access_token"))
    if create:
        data = call("POST", "/payments", {"amount_krw": amount}, protected=True)
        if data:
            state["payment_id"] = data["id"]
            st.success("결제 요청 생성 · 승인 대기")
    if state.get("access_token"):
        st.subheader("FIDO2 · WebAuthn 패스키로 결제 승인")
        st.caption("등록한 패스키의 공개키로 이 결제 요청에 대한 인증기 서명을 검증합니다.")
        st.link_button("패스키 승인 페이지 열기", BROWSER_API + "/section-2/webauthn/browser")
        with st.expander("승인 페이지에 입력할 실습용 JWT"):
            st.code(state["access_token"], language="text")
    if state.get("payment_id"):
        payment_id = state["payment_id"]
        st.caption("결제 ID")
        st.code(payment_id, language="text")
        if st.button("결제 상태와 영수증 확인"):
            data = call("GET", f"/payments/{payment_id}", protected=True)
            if data:
                if data["status"] == "completed":
                    st.success("결제 완료")
                    stored, decrypted = st.columns(2)
                    with stored:
                        st.markdown("**DB에 저장된 영수증 암호문**")
                        st.caption("AES-256-GCM")
                        st.code(data["encrypted_receipt"], language="text", wrap_lines=True)
                    receipt = call("GET", f"/payments/{payment_id}/receipt", protected=True)
                    if receipt:
                        with decrypted:
                            st.markdown("**권한 확인 후 복호화한 영수증**")
                            st.json(receipt)
                else:
                    st.info("결제 승인 대기 중입니다.")
