from contextlib import asynccontextmanager

from fastapi import FastAPI

from web.database import initialize
from web.routers import auth, oauth, payments, webauthn


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="Fintech Security Lab", lifespan=lifespan)


for router in (auth.router, oauth.router, payments.router, webauthn.router):
    app.include_router(router, prefix="/section-2", tags=["Section 2"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}
