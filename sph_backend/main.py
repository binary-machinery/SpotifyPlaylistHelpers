import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from sph_backend.api.routers import auth, playlists, misc
from sph_backend.settings import get_settings
from sph_backend.spotify.errors import SpotifyAuthError, SpotifyRateLimitError, SpotifyApiError


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


@app.exception_handler(SpotifyAuthError)
async def handle_spotify_auth_error(request: Request, exc: SpotifyAuthError):
    logging.error(f"Spotify authentication error: {exc}")
    return JSONResponse(
        status_code=401,
        content={"detail": "Spotify authentication failed, try to reauthenticate"}
    )


@app.exception_handler(SpotifyRateLimitError)
async def handle_spotify_rate_limit_error(request: Request, exc: SpotifyRateLimitError):
    logging.error(f"Spotify rate limit error: {exc}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Spotify rate limit, try later"},
        headers={
            "Retry-After": exc.retry_after
        } if exc.retry_after else None
    )


@app.exception_handler(SpotifyApiError)
async def handle_spotify_api_error(request: Request, exc: SpotifyApiError):
    logging.error(f"Spotify API error: {exc}")
    if exc.status_code == 404:
        status_code = 404
    elif exc.status_code // 100 == 5:
        status_code = 502
    else:
        status_code = exc.status_code
    return JSONResponse(
        status_code=status_code,
        content={"detail": "Spotify API error"}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
