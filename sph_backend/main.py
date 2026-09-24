import inspect
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
from sph_backend.users import UsersDb

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.users_db = UsersDb(users_db_path=get_settings().users_db_path)
    await app.state.users_db.create_schema()

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
def handle_spotify_auth_error(request: Request, exc: SpotifyAuthError):
    logger.debug("Enter handler for SpotifyAuthError")
    logger.warning("Spotify authentication error: %s", exc)
    return JSONResponse(
        status_code=401,
        content={"detail": "Spotify authentication failed, try to reauthenticate"}
    )


@app.exception_handler(SpotifyRateLimitError)
def handle_spotify_rate_limit_error(request: Request, exc: SpotifyRateLimitError):
    logger.debug("Enter handler for SpotifyRateLimitError: %s", exc)
    logger.error("Spotify rate limit error: %s", exc)
    return JSONResponse(
        status_code=429,
        content={"detail": "Spotify rate limit, try later"},
        headers={
            "Retry-After": exc.retry_after
        } if exc.retry_after else None
    )


@app.exception_handler(SpotifyApiError)
def handle_spotify_api_error(request: Request, exc: SpotifyApiError):
    logger.debug("Enter handler for SpotifyApiError: %s", exc)
    if exc.status_code == 404:
        status_code = 404
        log_level = logging.INFO
    elif exc.status_code // 100 == 5:
        status_code = 502
        log_level = logging.WARNING
    else:
        status_code = exc.status_code
        log_level = logging.WARNING
    logger.log(log_level, exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": "Spotify API error"}
    )


@app.exception_handler(ExceptionGroup)
async def handle_exception_group(request: Request, exc: ExceptionGroup):
    logger.debug("Enter handler for ExceptionGroup: %s", exc)
    inner_exc = exc
    while isinstance(inner_exc, ExceptionGroup):
        inner_exc = inner_exc.exceptions[0]
    for cls in type(inner_exc).__mro__:
        if cls in request.app.exception_handlers:
            res = request.app.exception_handlers[cls](request, inner_exc)
            if inspect.isawaitable(res):
                return await res
            return res

    logger.error("Unhandled exception in ExceptionGroup", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
