from typing import Annotated

import httpx
from fastapi import Depends
from starlette.exceptions import HTTPException
from starlette.requests import Request

from sph_backend.settings import get_settings
from sph_backend.spotify.client import SpotifyClient
from sph_backend.spotify.service import SpotifyPlaylistService
from sph_backend.users import UsersDb, User


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_users_db(request: Request) -> UsersDb:
    return request.app.state.users_db


def get_current_user(request: Request, users_db=Depends(get_users_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = users_db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_spotify_client(http_client=Depends(get_http_client), settings=Depends(get_settings),
                             users_db=Depends(get_users_db), current_user=Depends(get_current_user)) -> SpotifyClient:
    def on_token_refreshed(access_token: str, refresh_token: str):
        user = User(
            user_id=current_user.user_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        users_db.set_user(user)

    return SpotifyClient(
        http_client=http_client,
        settings=settings,
        access_token=current_user.access_token,
        refresh_token=current_user.refresh_token,
        on_token_refreshed=on_token_refreshed
    )


async def get_spotify_service(spotify_client=Depends(get_spotify_client)) -> SpotifyPlaylistService:
    return SpotifyPlaylistService(spotify_client=spotify_client)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
SpotifyClientDep = Annotated[SpotifyClient, Depends(get_spotify_client)]
SpotifyServiceDep = Annotated[SpotifyPlaylistService, Depends(get_spotify_service)]
