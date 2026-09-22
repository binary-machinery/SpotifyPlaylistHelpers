import logging
import secrets
import urllib.parse

from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse

from sph_backend.api import schemas
from sph_backend.api.dependencies import UsersDbDep, \
    HttpClientDep, SettingsDep, SpotifyClientDep
from sph_backend.spotify.auth import SpotifyAuth
from sph_backend.spotify.client import SpotifyClient
from sph_backend.users import User

router = APIRouter(
    tags=["auth"]
)


@router.get("/auth", response_class=RedirectResponse, status_code=307)
async def auth(request: Request, settings: SettingsDep):
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "scope": "playlist-modify-public playlist-read-private playlist-modify-private",
        "redirect_uri": settings.server_host + "/auth_callback",
        "state": state
    }
    return RedirectResponse(auth_url + "?" + urllib.parse.urlencode(params))


@router.get("/me")
async def me(spotify_client: SpotifyClientDep) -> schemas.SpotifyUser:
    user_json = await spotify_client.get("/me")
    return schemas.SpotifyUser(
        id=user_json["id"],
        display_name=user_json.get("display_name")
    )


@router.post("/logout")
async def logout(request: Request, users_db: UsersDbDep) -> schemas.AuthStatus:
    user_id = request.session.get("user_id")
    request.session.clear()
    if user_id is not None and isinstance(user_id, str):
        users_db.delete_user(user_id)
    return schemas.AuthStatus(status="logged out")


@router.get("/auth_callback")
async def auth_callback(request: Request, settings: SettingsDep, http_client: HttpClientDep,
                        users_db: UsersDbDep) -> schemas.AuthStatus:
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or not secrets.compare_digest(request.query_params.get("state", ""), expected_state):
        logging.warning("Spotify Auth Error: Invalid OAuth state")
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    if "error" in request.query_params:
        logging.warning("Spotify Auth Error: %s", request.query_params["error"])
        raise HTTPException(status_code=400, detail="Spotify Auth Error")

    code = request.query_params.get("code")
    if not code:
        logging.warning("Spotify Auth Error: No `code` in the Spotify Auth request")
        raise HTTPException(status_code=400, detail="No `code` in the Spotify Auth request")

    auth_response_json = await SpotifyAuth(http_client=http_client, settings=settings).token(code)
    access_token = auth_response_json["access_token"]
    refresh_token = auth_response_json["refresh_token"]

    user_data_json = await SpotifyClient(
        http_client=http_client,
        settings=settings,
        access_token=access_token,
        refresh_token=refresh_token
    ).get("/me")
    user = User(
        user_data_json["id"],
        access_token,
        refresh_token
    )
    users_db.set_user(user)
    request.session["user_id"] = user.user_id

    return schemas.AuthStatus(status="authenticated")
