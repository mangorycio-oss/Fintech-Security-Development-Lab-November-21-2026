# Fintech Security Development Lab

**강의일 · 2026년 11월 21일**

가상 은행을 연결하고 결제를 승인하는 흐름으로 금융 서비스의 보안 기술을 실습합니다.

## 시작하기

Git과 Docker Compose가 필요합니다. Docker가 실행 중인 상태에서 아래 명령을 실행하세요.

```bash
git clone https://github.com/mangorycio-oss/Fintech-Security-Development-Lab-November-21-2026.git
cd Fintech-Security-Development-Lab-November-21-2026
docker compose up --build -d
```

| 화면 | 주소 |
|---|---|
| 실습 웹 화면 | [localhost:8501](http://localhost:8501) |
| 웹 API 문서 | [localhost:8000/docs](http://localhost:8000/docs) |
| 가상 은행 API 문서 | [localhost:8001/docs](http://localhost:8001/docs) |

패스키 실습에는 WebAuthn과 RS256(RSA 서명)을 지원하는 브라우저 및 인증기가 필요합니다. 실습 환경에는 가상 계정과 테스트 데이터만 입력하세요.

실습을 마쳤으면 `docker compose down`으로 종료합니다. 웹 앱의 실습 계정과 패스키 등록은 웹 API가 재시작되면 초기화됩니다.

## 실습 순서

1. **시큐어 코딩** · SQL Injection, XSS, CSRF 방어 적용 전후를 비교합니다.
2. **인증과 결제** · 가입과 MFA 로그인, 가상 은행 동의, 결제 요청과 패스키 승인, 암호화 영수증 조회를 진행합니다. [세션 2 안내](web/README.md)
3. **보안 테스트와 DevSecOps** · 현재 프로젝트를 대상으로 검사 결과를 확인하고 CI에 연결하는 실습을 진행합니다.

## 코드 위치

- `web/` · 웹 API와 시큐어 코딩 실습
- `bank/` · 가상 은행 API와 동의 화면
- `frontend/` · Streamlit 실습 화면
- `gateway/` · Nginx API Gateway 설정
- `shared/` · 웹과 은행이 함께 사용하는 요청 규칙과 유틸리티
- `tests/` · 인증, 은행 동의, 결제, Gateway 자동화 테스트
