import secrets
import urllib.parse
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Depends
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from sph_backend.settings import get_settings
from sph_backend.spotify_api import SpotifyAuth, SpotifyApi
from sph_backend.users import UsersDb, User


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

_users_db = UsersDb()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_users_db() -> UsersDb:
    return _users_db


async def get_current_user(request: Request, users_db=Depends(get_users_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = users_db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_spotify_api(http_client=Depends(get_http_client), settings=Depends(get_settings),
                          users_db=Depends(get_users_db), current_user=Depends(get_current_user)) -> SpotifyApi:
    return SpotifyApi(
        http_client=http_client,
        settings=settings,
        users_db=users_db,
        access_token=current_user.access_token,
        refresh_token=current_user.refresh_token
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/auth")
async def auth(request: Request, settings=Depends(get_settings)):
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url = "https://accounts.spotify.com/authorize?"
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "scope": "playlist-modify-public playlist-read-private playlist-modify-private",
        "redirect_uri": settings.server_host + "/auth_callback",
        "state": state
    }
    return RedirectResponse(auth_url + urllib.parse.urlencode(params))


@app.get("/auth_callback")
async def auth_callback(request: Request, settings=Depends(get_settings),
                        http_client=Depends(get_http_client), users_db=Depends(get_users_db)):
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or not secrets.compare_digest(request.query_params.get("state", ""), expected_state):
        return Response("Invalid OAuth state", status_code=400)

    code = request.query_params.get("code")
    if not code:
        return Response(request.query_params.get("error"), status_code=400)

    auth_response: httpx.Response = await SpotifyAuth(http_client=http_client, settings=settings).token(code)
    if not auth_response.is_success:
        return Response(auth_response.text, status_code=auth_response.status_code)

    access_token = auth_response.json().get("access_token")
    refresh_token = auth_response.json().get("refresh_token")

    auth_response = await SpotifyApi(
        http_client=http_client,
        settings=settings,
        users_db=users_db,
        access_token=access_token,
        refresh_token=refresh_token
    ).get("/me")
    if auth_response.is_success:
        user = User(
            auth_response.json()["id"],
            access_token,
            refresh_token
        )
        users_db.set_user(user)
        request.session["user_id"] = user.user_id

    return {"status": "authenticated"}


@app.get("/me")
async def me(spotify_api: SpotifyApi = Depends(get_spotify_api)):
    response = await spotify_api.get("/me")
    return {
        "status": response.status_code,
        "res": response.json()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
