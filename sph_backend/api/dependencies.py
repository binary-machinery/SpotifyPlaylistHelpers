from typing import Annotated

import httpx
from fastapi import Depends, HTTPException
from starlette.requests import Request

from sph_backend.settings import Settings, get_settings
from sph_backend.spotify.web_api import SpotifyWebApi
from sph_backend.spotify.auth_api import SpotifyAuthApi
from sph_backend.spotify.session_client import SpotifySessionClient
from sph_backend.spotify.service import SpotifyPlaylistService
from sph_backend.users import UsersDb, User

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_users_db(request: Request) -> UsersDb:
    return request.app.state.users_db


UsersDbDep = Annotated[UsersDb, Depends(get_users_db)]


def get_current_user(request: Request, users_db: UsersDbDep) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=401, detail="Incorrect user id")
    user = users_db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_spotify_auth_api(http_client: HttpClientDep, settings: SettingsDep) -> SpotifyAuthApi:
    return SpotifyAuthApi(http_client=http_client, settings=settings)  # stateless wrapper


SpotifyAuthApiDep = Annotated[SpotifyAuthApi, Depends(get_spotify_auth_api)]


async def get_spotify_web_api(http_client: HttpClientDep) -> SpotifyWebApi:
    return SpotifyWebApi(http_client=http_client)  # stateless wrapper


SpotifyWebApiDep = Annotated[SpotifyWebApi, Depends(get_spotify_web_api)]


async def get_spotify_session_client(spotify_web_api: SpotifyWebApiDep, spotify_auth_api: SpotifyAuthApiDep,
                                     users_db: UsersDbDep, current_user: CurrentUserDep) -> SpotifySessionClient:
    def on_token_refreshed(access_token: str, refresh_token: str):
        user = User(
            user_id=current_user.user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        users_db.set_user(user)

    return SpotifySessionClient(
        spotify_web_api=spotify_web_api,
        spotify_auth_api=spotify_auth_api,
        access_token=current_user.access_token,
        refresh_token=current_user.refresh_token,
        on_token_refreshed=on_token_refreshed
    )


SpotifySessionClientDep = Annotated[SpotifySessionClient, Depends(get_spotify_session_client)]


async def get_spotify_service(spotify_session_client: SpotifySessionClientDep) -> SpotifyPlaylistService:
    return SpotifyPlaylistService(spotify_session_client=spotify_session_client)


SpotifyServiceDep = Annotated[SpotifyPlaylistService, Depends(get_spotify_service)]
