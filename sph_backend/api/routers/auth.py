import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from sph_backend.api.dependencies import get_users_db, get_current_user, get_http_client, get_spotify_client
from sph_backend.settings import get_settings
from sph_backend.spotify.auth import SpotifyAuth
from sph_backend.spotify.client import SpotifyClient
from sph_backend.users import User

router = APIRouter(
    tags=["auth"]
)


@router.get("/auth")
async def auth(request: Request, settings=Depends(get_settings)):
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
async def me(spotify_client: SpotifyClient = Depends(get_spotify_client)):
    user = await spotify_client.get("/me")
    return {
        "res": user
    }


@router.post("/logout")
async def logout(request: Request, users_db=Depends(get_users_db), current_user=Depends(get_current_user)):
    request.session.clear()
    users_db.delete_user(current_user.user_id)
    return {"status": "logged out"}


@router.get("/auth_callback")
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

    user_data_json = await SpotifyClient(
        http_client=http_client,
        settings=settings,
        users_db=users_db,
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

    return {"status": "authenticated"}
