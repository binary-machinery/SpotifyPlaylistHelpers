from typing import Literal, Self

from pydantic import BaseModel

from sph_backend.spotify import models


class Page[T](BaseModel):
    total: int
    items: list[T]


class Health(BaseModel):
    status: Literal["ok"]


class AuthStatus(BaseModel):
    status: Literal["authenticated", "logged out"]


class SpotifyUser(BaseModel):
    id: str
    display_name: str | None = None


class SimplifiedPlaylist(BaseModel):
    id: str
    name: str
    owner: str

    @classmethod
    def from_domain(cls, playlist: models.SimplifiedPlaylist) -> Self:
        return cls(id=playlist.id, name=playlist.name, owner=playlist.owner)
