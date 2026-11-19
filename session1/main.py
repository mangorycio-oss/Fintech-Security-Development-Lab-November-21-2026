from fastapi import FastAPI

from routers import csrf, sql, xss

app = FastAPI(title="Session 1 · 시큐어 코딩")

for router in (sql.router, xss.router, csrf.router):
    app.include_router(router, prefix="/section-1", tags=["Section 1"])
