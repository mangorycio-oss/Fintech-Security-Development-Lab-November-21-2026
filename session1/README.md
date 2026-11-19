# 세션 1 · 시큐어 코딩

이 폴더에서 SQL Injection, XSS, CSRF 개선 전후를 비교합니다.

저장소 루트에서 실행합니다.

```bash
cd session1
docker compose up --build -d --wait
```

- [Streamlit 실습 화면](http://localhost:8502)
- [FastAPI 문서](http://localhost:8002/docs)

`routers/`는 실습 API, `frontend/`는 Streamlit 화면입니다. 종료할 때는 같은 폴더에서 `docker compose down`을 실행합니다.
