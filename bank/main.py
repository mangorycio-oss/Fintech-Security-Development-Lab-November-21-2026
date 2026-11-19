import os
import secrets
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bank.database import initialize
from bank.routers import oauth, resources
from shared.bank_identity import KEY_PATH


@asynccontextmanager
async def lifespan(app):
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not KEY_PATH.exists():
        with tempfile.NamedTemporaryFile(dir=KEY_PATH.parent, delete=False) as key:
            key.write(secrets.token_bytes(32))
        os.replace(key.name, KEY_PATH)
    initialize()
    yield


app = FastAPI(title="Fintech Lab Bank", lifespan=lifespan)
app.include_router(oauth.router)
app.include_router(resources.router)
