import base64
import datetime
import json
import urllib.parse
from dataclasses import dataclass

import requests

from users import User


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
    release_date: datetime
    link: str


@dataclass
class Track:
    id: str
    name: str
    artists: list[Artist]
    album: Album


class SpotifyAuth:
    def __init__(self, config):
        self.api_url = "https://accounts.spotify.com/api"
        self.host = config["server"]["host"]

        client_id = config["spotify"]["client_id"]
        client_secret = config["spotify"]["client_secret"]
        basic_auth = "Basic " + base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": basic_auth
        }

    def token(self, code):
        return requests.post(
            self.api_url + "/token",
            headers=self.headers,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.host + "/auth_callback"
            }
        )

    def refresh_token(self, refresh_token):
        return requests.post(
            self.api_url + "/token",
            headers=self.headers,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )


class SpotifyApi:
    def __init__(self, config, users_db, access_token, refresh_token):
        self.api_url = "https://api.spotify.com/v1"
        self.config = config
        self.users_db = users_db
        self.access_token = access_token
        self.refresh_token = refresh_token

    def _refresh_token(self):
        auth_response = SpotifyAuth(self.config).refresh_token(self.refresh_token)
        if auth_response.ok:
            self.access_token = auth_response.json().get("access_token")
            self.refresh_token = auth_response.json().get("refresh_token", self.refresh_token)
            response = self.get("/me")
            if response.ok:
                user = User(
                    response.json()["id"],
                    self.access_token,
                    self.refresh_token
                )
                self.users_db.set_user(user)

    def get(self, endpoint, params=None):
        if params is None:
            params = {}

        response = requests.get(
            f"{self.api_url}{endpoint}?{urllib.parse.urlencode(params)}",
            headers={
                "Authorization": f"Bearer {self.access_token}"
            }
        )

        if not response.ok and response.status_code == 401:
            self._refresh_token()
            response = requests.get(
                f"{self.api_url}{endpoint}?{urllib.parse.urlencode(params)}",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                }
            )

        return response

    def get_paginated_items(self, endpoint, params, limit):
        params["limit"] = limit
        has_data = True
        offset = 0
        items = []
        while has_data:
            params["offset"] = offset
            response = self.get(endpoint, params)
            if not response.ok:
                return items

            json = response.json()
            items.extend(json["items"])
            has_data = False
            if json["total"] > offset + limit:
                has_data = True
                offset += limit

        return items

    def post(self, endpoint, params=None, data=None):
        if params is None:
            params = {}

        response = requests.post(
            f"{self.api_url}{endpoint}?{urllib.parse.urlencode(params)}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            data=data
        )

        if not response.ok and response.status_code == 401:
            self._refresh_token()
            response = requests.post(
                f"{self.api_url}{endpoint}?{urllib.parse.urlencode(params)}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                data=data
            )

        return response

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
        response = self.get("/me/playlists")
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
        response = self.get(f"/playlists/{playlist_id}?fields=id,name,owner(display_name)")
        if not response.ok:
            return None, None

        json = response.json()
        playlist = Playlist(
            json["id"],
            json["name"],
            json["owner"]["display_name"]
        )

        items = self.get_paginated_items(
            endpoint=f"/playlists/{playlist_id}/tracks",
            params={
                "fields": "total,items(track(id,name,album(id,name,release_date,release_date_precision,external_urls(spotify)),artists(id,name,external_urls(spotify))))"
            },
            limit=50
        )

        tracks = []
        for track_meta_json in items:
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

        return playlist, tracks

    def get_latest_song_by_artist(self, playlist_id):
        playlist, tracks = self.get_playlist(playlist_id)
        result = {}
        for track in tracks:
            if track.artists[0].id is None:
                continue
            latest = max(track.album.release_date, result.get(track.artists[0], datetime.datetime.fromtimestamp(0)))
            result[track.artists[0]] = latest
        return result

    def get_new_releases_for_playlist(self, playlist_id):
        latest_dates = self.get_latest_song_by_artist(playlist_id)
        result = {}
        for artist, latest_song_date in latest_dates.items():
            items = self.get_paginated_items(
                endpoint=f"/artists/{artist.id}/albums",
                params={
                    "market": "FI",
                    "include_groups": "album,single"
                },
                limit=20
            )

            for album_json in items:
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

        return latest_dates, result

    def add_artist_to_playlist(self, playlist_id, artist_id):
        items = self.get_paginated_items(
            endpoint=f"/artists/{artist_id}/albums",
            params={
                "market": "FI",
                "include_groups": "album,single"
            },
            limit=20
        )

        albums = []
        for album_json in items:
            album = Album(
                album_json["id"],
                album_json["name"],
                self._parse_album_date(album_json),
                album_json["external_urls"]["spotify"]
            )
            albums.append(album)

        albums.sort(key=lambda x: x.release_date)
        track_uris = []
        for album in albums:
            items = self.get_paginated_items(
                f"/albums/{album.id}/tracks",
                params={
                    "market": "FI"
                },
                limit=50
            )

            for track_json in items:
                track_uris.append(track_json["uri"])

        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            self.post(
                f"/playlists/{playlist_id}/tracks",
                data=json.dumps({"uris": chunk})
            )
