from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, computed_field

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


class Artist(BaseModel):
    id: str
    name: str
    link: str

    @classmethod
    def from_domain(cls, artist: models.Artist) -> Self:
        return cls(id=artist.id, name=artist.name, link=artist.link)


class Album(BaseModel):
    id: str
    name: str
    release_date: date
    link: str

    @classmethod
    def from_domain(cls, album: models.Album) -> Self:
        return cls(id=album.id, name=album.name, release_date=album.release_date.date(), link=album.link)


class ArtistReleases(BaseModel):
    artist: Artist
    releases: list[Album]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.releases)

    @classmethod
    def from_domain(cls, artist: models.Artist, releases: list[models.Album]) -> Self:
        return cls(
            artist=Artist.from_domain(artist),
            releases=[Album.from_domain(album) for album in releases],
        )
