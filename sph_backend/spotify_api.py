import base64
import datetime
import json
import urllib.parse
from dataclasses import dataclass

import httpx

from sph_backend.settings import Settings
from sph_backend.users import User, UsersDb


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
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self._http_client = http_client
        self._api_url = "https://accounts.spotify.com/api"
        self._server_host = settings.server_host

        client_id = settings.spotify_client_id
        client_secret = settings.spotify_client_secret.get_secret_value()
        basic_auth = "Basic " + base64.b64encode(bytes(f"{client_id}:{client_secret}", "utf-8")).decode("utf-8")
        self._headers = {
            "Authorization": basic_auth
        }

    async def token(self, code: str) -> httpx.Response:
        return await self._http_client.post(
            self._api_url + "/token",
            headers=self._headers,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._server_host + "/auth_callback"
            }
        )

    async def update_token(self, refresh_token: str) -> httpx.Response:
        return await self._http_client.post(
            self._api_url + "/token",
            headers=self._headers,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )


class SpotifyApi:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings, users_db: UsersDb,
                 access_token: str, refresh_token: str):
        self._http_client = http_client
        self._api_url = "https://api.spotify.com/v1"
        self._settings = settings
        self._users_db = users_db
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def _update_token(self):
        auth_response = await SpotifyAuth(self._http_client, self._settings).update_token(self._refresh_token)
        if auth_response.is_success:
            auth_response_json = auth_response.json()
            self._access_token = auth_response_json.get("access_token")
            self._refresh_token = auth_response_json.get("refresh_token", self._refresh_token)
            response = await self.get("/me")
            if response.is_success:
                user = User(
                    response.json()["id"],
                    self._access_token,
                    self._refresh_token
                )
                self._users_db.set_user(user)

    async def _http(self, method: str, endpoint: str, params=None, data=None, retry=True) -> httpx.Response:
        if params is None:
            params = {}

        response = await self._http_client.request(
            method=method,
            url=f"{self._api_url}{endpoint}?{urllib.parse.urlencode(params)}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json"
            },
            data=data
        )

        if not response.is_success and response.status_code == 401 and retry:
            await self._update_token()
            response = await self._http(method, endpoint, params, data, retry=False)

        return response

    async def get(self, endpoint, params=None, data=None, retry=True) -> httpx.Response:
        return await self._http("GET", endpoint, params, data, retry)

    async def post(self, endpoint, params=None, data=None, retry=True) -> httpx.Response:
        return await self._http("POST", endpoint, params, data, retry)

    async def put(self, endpoint, params=None, data=None, retry=True) -> httpx.Response:
        return await self._http("PUT", endpoint, params, data, retry)

    async def delete(self, endpoint, params=None, data=None, retry=True) -> httpx.Response:
        return await self._http("DELETE", endpoint, params, data, retry)

    def get_paginated_items(self, endpoint, params=None, limit=20):
        if params is None:
            params = {}
        params["limit"] = limit
        has_data = True
        offset = 0
        items = []
        while has_data:
            params["offset"] = offset
            response = self.get(endpoint, params)
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")

            json = response.json()
            items.extend(json["items"])
            has_data = False
            if json["total"] > offset + limit:
                has_data = True
                offset += limit

        return items

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
        has_data = True
        offset = 0
        playlists = []
        while has_data:
            response = self.get("/me/playlists", {"offset": offset})
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")

            json = response.json()
            for playlist_json in json["items"]:
                playlist = Playlist(
                    playlist_json["id"],
                    playlist_json["name"],
                    playlist_json["owner"]["display_name"]
                )
                playlists.append(playlist)

            has_data = False
            if json["total"] > offset + json["limit"]:
                offset += json["limit"]
                has_data = True

        return playlists

    def get_playlist(self, playlist_id):
        response = self.get(f"/playlists/{playlist_id}?fields=id,name,owner(display_name)")
        if not response.ok:
            raise Exception(f"{response.status_code}: {response.text}")

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

        for artist_result in result.values():
            artist_result.sort(key=lambda album: album.release_date)
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
            response = self.post(
                f"/playlists/{playlist_id}/tracks",
                data=json.dumps({"uris": chunk})
            )
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")

    def subtract_playlist(self, playlist_id1, playlist_id2):
        items = self.get_paginated_items(
            f"/playlists/{playlist_id2}/tracks",
            limit=50
        )

        track_jsons = []
        for item in items:
            track_json = {"uri": item["track"]["uri"]}
            track_jsons.append(track_json)

        for i in range(0, len(track_jsons), 100):
            chunk = track_jsons[i:i + 100]
            response = self.delete(
                f"/playlists/{playlist_id1}/tracks",
                data=json.dumps({"tracks": chunk})
            )
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")

    def filter_playlist(self, user_id, playlist_id, keyword):
        response = self.get(f"/playlists/{playlist_id}")
        if not response.ok:
            raise Exception(f"{response.status_code}: {response.text}")

        playlist_name = response.json()["name"]

        items = self.get_paginated_items(
            f"/playlists/{playlist_id}/tracks",
            limit=50
        )

        track_uris = []
        for item in items:
            if keyword in item["track"]["name"].lower():
                track_uris.append(item["track"]["uri"])

        response = self.post(
            f"/users/{user_id}/playlists",
            data=json.dumps(
                {
                    "name": f"delivery-{keyword}-{playlist_name}",
                    "public": False
                }
            )
        )
        if not response.ok:
            raise Exception(f"{response.status_code}: {response.text}")

        tmp_playlist_id = response.json()["id"]
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            response = self.post(
                f"/playlists/{tmp_playlist_id}/tracks",
                data=json.dumps({"uris": chunk})
            )
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")

    def filter_duplicates(self, user_id, playlist_id):
        response = self.get(f"/playlists/{playlist_id}")
        if not response.ok:
            raise Exception(f"{response.status_code}: {response.text}")

        playlist_name = response.json()["name"]

        items = self.get_paginated_items(
            f"/playlists/{playlist_id}/tracks",
            limit=50
        )

        track_uris = []
        for i in range(0, len(items)):
            track_i = items[i]["track"]
            for j in range(i + 1, len(items)):
                track_j = items[j]["track"]
                if len(track_i["artists"]) != len(track_j["artists"]):
                    continue
                for k in range(0, len(track_i["artists"])):
                    if track_i["artists"][k]["id"] != track_j["artists"][k]["id"]:
                        continue
                if track_i["name"] == track_j["name"]:
                    release_date_i = self._parse_album_date(track_i["album"])
                    release_date_j = self._parse_album_date(track_j["album"])
                    if release_date_i < release_date_j:
                        if track_i["uri"] not in track_uris:
                            track_uris.append(track_i["uri"])
                    else:
                        if track_j["uri"] not in track_uris:
                            track_uris.append(track_j["uri"])
                    continue

        response = self.post(
            f"/users/{user_id}/playlists",
            data=json.dumps(
                {
                    "name": f"delivery-duplicates-{playlist_name}",
                    "public": False
                }
            )
        )
        if not response.ok:
            raise Exception(f"{response.status_code}: {response.text}")

        tmp_playlist_id = response.json()["id"]
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            response = self.post(
                f"/playlists/{tmp_playlist_id}/tracks",
                data=json.dumps({"uris": chunk})
            )
            if not response.ok:
                raise Exception(f"{response.status_code}: {response.text}")
