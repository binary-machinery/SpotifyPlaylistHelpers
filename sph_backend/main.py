from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from sph_backend.api.routers import auth, playlists, misc
from sph_backend.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().server_secret.get_secret_value(),
    same_site="lax"
)
app.include_router(auth.router)
app.include_router(playlists.router)
app.include_router(misc.router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
