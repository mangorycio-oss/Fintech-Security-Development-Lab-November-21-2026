# Section 2 · 핀테크 인증과 결제 보안

가입한 사용자만 계좌를 연결하고, 은행에 동의한 권한으로 결제를 요청한 뒤, 등록한 패스키로 승인하는 실습입니다. 결제가 완료되면 SQLite에 저장된 영수증 암호문과 소유권 확인 후 복호화한 영수증을 비교합니다.

## 실행

프로젝트 루트에서 실행합니다.

```bash
docker compose up --build -d
```

- [Streamlit Section 2](http://localhost:8501/section2)에서 가입부터 결제까지 진행합니다.
- [Swagger](http://localhost:8000/docs)에서 `/section-2` API를 직접 확인할 수 있습니다.

## 실습 순서

| 단계 | 사용 기술 | 화면에서 확인할 결과 |
| --- | --- | --- |
| ① 회원가입 | Argon2id | DB의 비밀번호 필드에는 해시가 저장됩니다. 가입 화면에서 실습 계정의 TOTP 설정 키를 받습니다. |
| ② 로그인 | TOTP, JWT | 설정 키를 **TOTP 인증기** 탭에 입력해 6자리 코드를 생성합니다. 비밀번호 확인과 TOTP 검증을 모두 통과해야 JWT가 발급됩니다. |
| ③ 계좌 연결 | Authorization Code, PKCE S256 | 연결 링크를 열고 은행 화면에서 계좌 조회·결제 요청을 선택합니다. 돌아온 뒤 기존 탭에서 연결 상태를 확인합니다. |
| ④ 결제 요청 | JWT 검증, 인가, Rate Limiting | 결제는 승인 대기로 생성됩니다. 같은 계정이 60초 고정 구간에서 네 번째 요청을 보내면 `429`가 반환됩니다. |
| ⑤ 결제 승인 | FIDO2/WebAuthn | **패스키 승인 페이지 열기**를 눌러 실습용 JWT로 패스키를 등록합니다. 결제 ID를 입력하고 금액을 확인한 뒤 인증기로 승인합니다. |
| ⑥ 결제 완료 | AES-256-GCM | 가상 은행에서 결제를 완료합니다. Streamlit에서 **결제 상태와 영수증 확인**을 누르면 저장된 암호문과 복호화된 영수증이 나란히 표시됩니다. |

## 백엔드 폴더

- [web/](.) · 웹 API. `main.py`에서 세션 2 라우터와 세션 1 실습을 등록합니다.
- [bank/](../bank/) · 은행 API. `main.py`에서 은행 라우터를 등록하고 `database.py`에서 은행 DB를 준비합니다. `routers/`는 HTTP 요청을 받고 `services.py`는 결제를 처리합니다.
- [shared/](../shared/) · 양쪽에서 쓰는 OAuth 요청 규칙, 결제 요청 모델, 일회용 값과 DB 도구.

## 코드 위치

| 위치 | 역할 |
| --- | --- |
| [routers/auth.py](routers/auth.py) | 가입, 비밀번호 검증, TOTP 챌린지, JWT 발급 |
| [routers/oauth.py](routers/oauth.py) | 연결 시작, 콜백 검증, 은행 토큰 저장과 계좌 조회 중개 |
| [bank/routers/oauth.py](../bank/routers/oauth.py) · [bank/routers/resources.py](../bank/routers/resources.py) | 은행 동의·코드 교환과 계좌·결제 |
| [routers/payments.py](routers/payments.py) | 결제 요청, 요청량 제한, 소유권 확인, 영수증 조회 |
| [routers/webauthn.py](routers/webauthn.py) · [webauthn.html](routers/webauthn.html) | 브라우저 패스키 등록, 결제별 챌린지와 공개키 서명 검증 |
| [security/](security/) | 비밀번호 해시, JWT, TOTP, 요청량 제한, 영수증 암호화 |
| [services/](services/) | 웹 API에서 은행 호출, 결제 상태와 영수증 처리 |
| [models.py](models.py) · [database.py](database.py) | 요청 모델, 일회용 챌린지, SQLite 스키마와 트랜잭션 |
| [frontend/section2.py](../frontend/section2.py) | Streamlit 실습 화면 |
| [tests/section2/](../tests/section2/) | 인증, 만료되거나 서명이 잘못된 JWT, PKCE와 동의 범위, 결제 승인, 암호화 검증 |

## 암호 기술이 쓰이는 위치

- **WebAuthn**은 새 패스키 등록 시 **RS256**(RSA와 SHA-256을 사용하는 서명)만 허용합니다. 결제 승인 시 등록된 공개키로 서명을 확인합니다.
- **AES-256-GCM**은 실제 실습 결제의 영수증을 암호화합니다.

## 실습 범위

은행과 결제는 로컬 가상 서비스입니다. 계좌 연결은 브라우저에서 가상 은행 화면으로 이동한 뒤 콜백으로 돌아옵니다. 은행 로그인은 생략하고 브라우저별 실습 계좌에 대한 동의만 받습니다. TOTP 인증기는 같은 Streamlit 세션에서 동작하는 실습용입니다. 패스키는 기본 설정에서 `http://localhost:8000`의 브라우저 화면을 사용합니다. API 프로세스를 재시작하면 임시 SQLite 데이터와 실행 시 생성한 키가 초기화됩니다.
