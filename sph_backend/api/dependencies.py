from typing import Annotated

import httpx
from fastapi import Depends
from starlette.exceptions import HTTPException
from starlette.requests import Request

from sph_backend.settings import get_settings
from sph_backend.spotify.client import SpotifyClient
from sph_backend.spotify.service import SpotifyPlaylistService
from sph_backend.users import UsersDb, User

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


async def get_spotify_client(http_client=Depends(get_http_client), settings=Depends(get_settings),
                             users_db=Depends(get_users_db), current_user=Depends(get_current_user)) -> SpotifyClient:
    return SpotifyClient(
        http_client=http_client,
        settings=settings,
        users_db=users_db,
        access_token=current_user.access_token,
        refresh_token=current_user.refresh_token
    )


async def get_spotify_service(spotify_client=Depends(get_spotify_client)) -> SpotifyPlaylistService:
    return SpotifyPlaylistService(spotify_client=spotify_client)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
SpotifyClientDep = Annotated[SpotifyClient, Depends(get_spotify_client)]
SpotifyServiceDep = Annotated[SpotifyPlaylistService, Depends(get_spotify_service)]
