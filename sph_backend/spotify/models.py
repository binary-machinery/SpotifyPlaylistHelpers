from dataclasses import dataclass
from datetime import datetime


@dataclass
class Artist:
    id: str
    name: str
    link: str

    def __hash__(self) -> int:
        return self.id.__hash__()


@dataclass
class Album:
    id: str
    name: str
    release_date: datetime
    link: str


@dataclass
class Track:
    id: str
    uri: str
    name: str
    artists: list[Artist]
    album: Album


@dataclass
class SimplifiedPlaylist:
    id: str
    name: str
    owner: str


@dataclass
class Playlist:
    id: str
    name: str
    owner: str
    tracks: list[Track]
