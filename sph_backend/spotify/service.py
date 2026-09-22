from datetime import datetime

from sph_backend.spotify.client import SpotifyClient
from sph_backend.spotify.models import SimplifiedPlaylist, Playlist, Album, Artist, Track


class SpotifyPlaylistService:
    def __init__(self, spotify_client: SpotifyClient):
        self._spotify_client = spotify_client

    async def get_playlists(self) -> list[SimplifiedPlaylist]:
        json = await self._spotify_client.get_paginated_items(
            endpoint="/me/playlists",
            limit=50
        )
        playlists = []
        for playlist_json in json:
            playlist = SimplifiedPlaylist(
                playlist_json["id"],
                playlist_json["name"],
                playlist_json["owner"]["display_name"]
            )
            playlists.append(playlist)

        return playlists

    async def get_playlist(self, playlist_id: str) -> Playlist:
        playlist_json = await self._spotify_client.get(
            f"/playlists/{playlist_id}",
            params={
                "fields": "id,name,owner(display_name)"
            }
        )
        tracks_json = await self._spotify_client.get_paginated_items(
            endpoint=f"/playlists/{playlist_id}/items",
            params={
                "fields": "total,items(track(id,name,album(id,name,release_date,release_date_precision,external_urls(spotify)),artists(id,name,external_urls(spotify))))"
            },
            limit=50
        )

        tracks = []
        for track_meta_json in tracks_json:
            track_json = track_meta_json.get("track")
            if track_json is None:
                continue

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

        return Playlist(
            id=playlist_json["id"],
            name=playlist_json["name"],
            owner=playlist_json["owner"]["display_name"],
            tracks=tracks
        )

    async def get_new_releases_for_playlist(self, playlist_id: str):
        latest_dates = await self._get_latest_song_by_artist_for_playlist(playlist_id)
        result = {}
        for artist, latest_song_date in latest_dates.items():
            items = await self._spotify_client.get_paginated_items(
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

    async def add_artist_to_playlist(self, playlist_id: str, artist_id: str) -> None:
        albums_json = await self._spotify_client.get_paginated_items(
            endpoint=f"/artists/{artist_id}/albums",
            params={
                "market": "FI",
                "include_groups": "album,single"
            },
            limit=20
        )

        albums = []
        for album_json in albums_json:
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
            tracks_json = await self._spotify_client.get_paginated_items(
                f"/albums/{album.id}/tracks",
                params={
                    "market": "FI"
                },
                limit=50
            )

            for track_json in tracks_json:
                track_uris.append(track_json["uri"])

        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            await self._spotify_client.post(
                f"/playlists/{playlist_id}/items",
                json={"uris": chunk}
            )

    async def subtract_playlist(self, playlist_id1: str, playlist_id2: str) -> None:
        # TODO: return amount of deleted tracks
        playlist2_tracks = await self._spotify_client.get_paginated_items(
            f"/playlists/{playlist_id2}/items",
            limit=50
        )

        track_jsons = []
        for item in playlist2_tracks:
            track_json = {"uri": item["track"]["uri"]}
            track_jsons.append(track_json)

        # TODO: move playlist write to a separate function
        for i in range(0, len(track_jsons), 100):
            chunk = track_jsons[i:i + 100]
            await self._spotify_client.delete(
                f"/playlists/{playlist_id1}/items",
                json={"items": chunk}
            )

    async def find_tracks_in_playlist(
            self, playlist_id: str, keyword: str, result_playlist_id: str | None = None
    ) -> None:
        # TODO: return link to the result playlist and amount of found tracks
        # TODO: call get_playlist here (and add uri to Track)
        simplified_playlist_json = await self._spotify_client.get(
            f"/playlists/{playlist_id}",
            params={"fields": "name"}
        )
        playlist_name = simplified_playlist_json["name"]

        items = await self._spotify_client.get_paginated_items(
            f"/playlists/{playlist_id}/items",
            limit=50
        )

        track_uris = []
        keyword = keyword.lower()
        for item in items:
            if keyword in item["track"]["name"].lower():
                track_uris.append(item["track"]["uri"])

        if result_playlist_id is None:
            # TODO: move playlist creation to a separate function
            result_json = await self._spotify_client.post(
                f"/me/playlists",
                json={"name": f"delivery-{keyword}-{playlist_name}", "public": False}
            )
            result_playlist_id = result_json["id"]

        # TODO: move playlist write to a separate function
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            await self._spotify_client.post(
                f"/playlists/{result_playlist_id}/items",
                json={"uris": chunk}
            )

    async def find_duplicates(self, playlist_id: str, result_playlist_id: str | None = None) -> None:
        # TODO: return link to the result playlist and amount of found tracks
        # TODO: call get_playlist here (and add uri to Track)
        simplified_playlist_json = await self._spotify_client.get(
            f"/playlists/{playlist_id}",
            params={"fields": "name"}
        )
        playlist_name = simplified_playlist_json["name"]

        items = await self._spotify_client.get_paginated_items(
            f"/playlists/{playlist_id}/items",
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

        if result_playlist_id is None:
            # TODO: move playlist creation to a separate function
            result_json = await self._spotify_client.post(
                f"/me/playlists",
                json={"name": f"delivery-duplicates-{playlist_name}", "public": False}
            )
            result_playlist_id = result_json["id"]

        # TODO: move playlist write to a separate function
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            await self._spotify_client.post(
                f"/playlists/{result_playlist_id}/items",
                json={"uris": chunk}
            )

    @staticmethod
    def _parse_album_date(album_json):
        if album_json["release_date_precision"] == "year":
            return datetime.strptime(album_json["release_date"], "%Y")
        elif album_json["release_date_precision"] == "month":
            return datetime.strptime(album_json["release_date"], "%Y-%m")
        elif album_json["release_date_precision"] == "day":
            return datetime.strptime(album_json["release_date"], "%Y-%m-%d")
        else:
            return datetime.fromtimestamp(0)

    async def _get_latest_song_by_artist_for_playlist(self, playlist_id: str) -> dict[Artist, datetime]:
        playlist = await self.get_playlist(playlist_id)
        result: dict[Artist, datetime] = {}
        for track in playlist.tracks:
            if track.artists[0].id is None:
                continue
            latest = max(track.album.release_date, result.get(track.artists[0], datetime.fromtimestamp(0)))
            result[track.artists[0]] = latest
        return result
