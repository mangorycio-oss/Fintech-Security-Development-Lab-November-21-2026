# Fintech Security Development Lab

**강의일 · 2026년 11월 21일**

가상 은행을 연결하고 결제를 승인하는 흐름으로 금융 서비스의 보안 기술을 실습합니다.

```bash
git clone https://github.com/mangorycio-oss/Fintech-Security-Development-Lab-November-21-2026.git
cd Fintech-Security-Development-Lab-November-21-2026
```

| 세션 | 폴더 | 실습 |
|---|---|---|
| 1 · 시큐어 코딩 | [session1/](session1/README.md) | SQL Injection, XSS, CSRF 개선 전후 비교 |
| 2 · 인증과 결제 | [session2/](session2/README.md) | MFA, OAuth, 패스키 승인, 암호화 영수증 |
| 3 · DevSecOps | [session3/](session3/README.md) | 자동화 테스트와 소스·의존성·이미지·실행 환경 보안 검사 |

세션 1과 2는 각각 해당 폴더에서 `docker compose up --build -d`로 실행합니다. 세션 1 화면은 [localhost:8502](http://localhost:8502), 세션 2 화면은 [localhost:8501](http://localhost:8501)에서 열립니다. 세션 3은 셸 스크립트와 [GitHub Actions 워크플로](.github/workflows/session-3.yml)로 세션 2 앱을 별도 환경에서 검사합니다.
