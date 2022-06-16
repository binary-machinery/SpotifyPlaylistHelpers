import datetime
from dataclasses import dataclass

from spotify_api import SpotifyApi


@dataclass
class Playlist:
    id: str
    name: str
    owner: str


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
    date: datetime
    link: str


@dataclass
class Track:
    id: str
    name: str
    artists: list[Artist]
    album: Album


class PlaylistNewReleases:
    def __init__(self, access_token):
        self.api = SpotifyApi(access_token)

    @staticmethod
    def _parse_album_date(album_json):
        if album_json["release_date_precision"] == "year":
            return datetime.datetime.strptime(album_json["release_date"], "%Y")
        elif album_json["release_date_precision"] == "month":
            return datetime.datetime.strptime(album_json["release_date"], "%Y-%m")
        elif album_json["release_date_precision"] == "day":
            return datetime.datetime.strptime(album_json["release_date"], "%Y-%m-%d")
        else:
            return datetime.datetime.fromtimestamp(0)

    def get_playlists(self):
        response = self.api.get("/me/playlists")
        playlists = []
        if not response.ok:
            return playlists

        for playlist_json in response.json()["items"]:
            playlist = Playlist(
                playlist_json["id"],
                playlist_json["name"],
                playlist_json["owner"]["display_name"]
            )
            playlists.append(playlist)

        return playlists

    def get_playlist(self, playlist_id):
        response = self.api.get(f"/playlists/{playlist_id}?fields=id,name,owner(display_name)")
        if not response.ok:
            return None, None

        json = response.json()
        playlist = Playlist(
            json["id"],
            json["name"],
            json["owner"]["display_name"]
        )

        has_data = True
        tracks = []
        limit = 50
        offset = 0
        while has_data:
            response = self.api.get(
                endpoint=f"/playlists/{playlist_id}/tracks",
                params={
                    "limit": limit,
                    "offset": offset,
                    "fields": "items(track(id,name,album(id,name,release_date,release_date_precision,external_urls(spotify)),artists(id,name,external_urls(spotify))))"
                }
            )
            if not response.ok:
                break

            has_data = False
            offset += limit

            json = response.json()
            for track_meta_json in json["items"]:
                track_json = track_meta_json["track"]

                album_json = track_json["album"]
                album = Album(
                    album_json["id"],
                    album_json["name"],
                    self._parse_album_date(album_json),
                    album_json["external_urls"]["spotify"]
                )

                artists = []
                for artist_json in track_json["artists"]:
                    artist = Artist(
                        artist_json["id"],
                        artist_json["name"],
                        artist_json["external_urls"]["spotify"]
                    )
                    artists.append(artist)

                track = Track(
                    track_json["id"],
                    track_json["name"],
                    artists,
                    album
                )
                tracks.append(track)
                has_data = True

        return playlist, tracks

    def get_latest_song_by_artist(self, playlist_id):
        playlist, tracks = self.get_playlist(playlist_id)
        result = {}
        for track in tracks:
            if track.artists[0].id is None:
                continue
            latest = max(track.album.date, result.get(track.artists[0], datetime.datetime.fromtimestamp(0)))
            result[track.artists[0]] = latest
        return result

    def get_new_releases_for_playlist(self, playlist_id):
        latest_dates = self.get_latest_song_by_artist(playlist_id)
        result = {}
        for artist, latest_song_date in latest_dates.items():
            has_data = True
            limit = 20
            offset = 0
            while has_data:
                response = self.api.get(
                    endpoint=f"/artists/{artist.id}/albums",
                    params={
                        "market": "FI",
                        "include_groups": "album,single",
                        "limit": limit,
                        "offset": offset
                    }
                )
                if not response.ok:
                    return result

                has_data = False
                offset += limit

                json = response.json()
                for album_json in json["items"]:
                    release_date = self._parse_album_date(album_json)
                    if release_date <= latest_song_date:
                        continue

                    album = Album(
                        album_json["id"],
                        album_json["name"],
                        release_date,
                        album_json["external_urls"]["spotify"]
                    )
                    if artist not in result:
                        result[artist] = []
                    result[artist].append(album)
                    has_data = True

        return latest_dates, result
