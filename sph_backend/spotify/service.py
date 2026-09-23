from datetime import datetime
from typing import Any

from sph_backend.spotify.errors import SpotifyApiError
from sph_backend.spotify.models import SimplifiedPlaylist, Playlist, Album, Artist, Track
from sph_backend.spotify.session_client import SpotifySessionClient


class SpotifyPlaylistService:
    def __init__(self, spotify_session_client: SpotifySessionClient):
        self._spotify_session_client = spotify_session_client

    async def get_playlists(self) -> list[SimplifiedPlaylist]:
        items = await self._spotify_session_client.get_paginated_items(
            endpoint="/me/playlists",
            limit=50
        )
        playlists = []
        for playlist_json in items:
            playlist = SimplifiedPlaylist(
                id=playlist_json["id"],
                name=playlist_json["name"],
                owner=playlist_json["owner"]["display_name"]
            )
            playlists.append(playlist)

        return playlists

    async def get_playlist(self, playlist_id: str) -> Playlist:
        playlist_json = await self._spotify_session_client.get(
            f"/playlists/{playlist_id}",
            params={
                "fields": "id,name,owner(display_name)"
            }
        )
        tracks_json = await self._spotify_session_client.get_paginated_items(
            endpoint=f"/playlists/{playlist_id}/items",
            params={
                "fields": "total,items(track(id,uri,name,album(id,name,release_date,release_date_precision,external_urls(spotify)),artists(id,name,external_urls(spotify))))"
            },
            limit=50
        )

        tracks = []
        for track_meta_json in tracks_json:
            track_json: dict[str, Any] | None = track_meta_json.get("track")
            if track_json is None:
                continue

            album_json = track_json["album"]
            album = Album(
                id=album_json["id"],
                name=album_json["name"],
                release_date=self._parse_album_date(album_json),
                link=album_json["external_urls"]["spotify"]
            )

            artists = []
            for artist_json in track_json["artists"]:
                artist = Artist(
                    id=artist_json["id"],
                    name=artist_json["name"],
                    link=artist_json["external_urls"]["spotify"]
                )
                artists.append(artist)

            track = Track(
                id=track_json["id"],
                uri=track_json["uri"],
                name=track_json["name"],
                artists=artists,
                album=album
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
            items = await self._spotify_session_client.get_paginated_items(
                endpoint=f"/artists/{artist.id}/albums",
                params={
                    "market": "FI",
                    "include_groups": "album,single"
                },
                limit=50
            )

            for album_json in items:
                release_date = self._parse_album_date(album_json)
                if release_date <= latest_song_date:
                    continue

                album = Album(
                    id=album_json["id"],
                    name=album_json["name"],
                    release_date=release_date,
                    link=album_json["external_urls"]["spotify"]
                )
                if artist not in result:
                    result[artist] = []
                result[artist].append(album)

        for artist_result in result.values():
            artist_result.sort(key=lambda album: album.release_date)
        return latest_dates, result

    async def add_artist_to_playlist(self, playlist_id: str, artist_id: str) -> None:
        albums_json = await self._spotify_session_client.get_paginated_items(
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
                id=album_json["id"],
                name=album_json["name"],
                release_date=self._parse_album_date(album_json),
                link=album_json["external_urls"]["spotify"]
            )
            albums.append(album)

        albums.sort(key=lambda x: x.release_date)
        track_uris = []
        for album in albums:
            tracks_json = await self._spotify_session_client.get_paginated_items(
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
            await self._spotify_session_client.post(
                f"/playlists/{playlist_id}/items",
                json={"uris": chunk}
            )

    async def subtract_playlist(self, playlist_id1: str, playlist_id2: str) -> None:
        # TODO: return amount of deleted tracks
        playlist2_tracks = await self._spotify_session_client.get_paginated_items(
            f"/playlists/{playlist_id2}/items",
            limit=50
        )

        track_uris: list[dict[str, str]] = []
        for item in playlist2_tracks:
            track_uri = {"uri": item["track"]["uri"]}
            track_uris.append(track_uri)

        await self._delete_tracks_from_playlist(playlist_id=playlist_id1, uris=track_uris)

    async def extract_tracks_from_playlist(
            self, playlist_id: str, keyword: str, result_playlist_id: str | None = None
    ) -> None:
        # TODO: return link to the result playlist and amount of found tracks
        playlist = await self.get_playlist(playlist_id)
        track_uris = []
        keyword = keyword.lower()
        for track in playlist.tracks:
            if keyword in track.name.lower():
                track_uris.append(track.uri)

        if result_playlist_id is None:
            result_playlist_id = await self._create_playlist(f"{playlist.name}-{keyword}")

        if result_playlist_id is None:
            raise SpotifyApiError(status_code=502, body="Failed to create a playlist")

        await self._write_tracks_to_playlist(result_playlist_id, track_uris)

    async def extract_duplicates(self, playlist_id: str, result_playlist_id: str | None = None) -> None:
        # TODO: return link to the result playlist and amount of found tracks
        playlist = await self.get_playlist(playlist_id)
        duplicate_uris = {}  # use dict keys instead of set to keep order
        track_index: dict[str, Track] = {}
        for track in playlist.tracks:
            key = ":".join([artist.id for artist in track.artists])
            key += ":" + track.name
            if key not in track_index:
                track_index[key] = track
            else:
                prev_track = track_index[key]
                if track.album.release_date < prev_track.album.release_date:
                    duplicate_uris[track.uri] = None
                else:
                    duplicate_uris[prev_track.uri] = None
                    track_index[key] = track

        if result_playlist_id is None:
            result_playlist_id = await self._create_playlist(f"{playlist.name}-duplicates")

        if result_playlist_id is None:
            raise SpotifyApiError(status_code=502, body="Failed to create a playlist")

        await self._write_tracks_to_playlist(
            playlist_id=result_playlist_id,
            uris=list(duplicate_uris.keys())
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

    async def _create_playlist(self, playlist_name: str):
        result_json = await self._spotify_session_client.post(
            "/me/playlists",
            json={"name": playlist_name, "public": False}
        )
        return result_json["id"]

    async def _write_tracks_to_playlist(self, playlist_id: str, uris: list[str]) -> None:
        # uris param format: ["spotify:track:4iV5W9uYEdYUVa79Axb7Rh","spotify:track:1301WleyT98MSxVHPZCA6M", "spotify:episode:512ojhOuo1ktJprKbVcKyQ"]
        # Spotify API format: `{"uris": ["spotify:track:4iV5W9uYEdYUVa79Axb7Rh","spotify:track:1301WleyT98MSxVHPZCA6M", "spotify:episode:512ojhOuo1ktJprKbVcKyQ"]}`
        await self._spotify_session_client.post_in_chunks(
            endpoint=f"/playlists/{playlist_id}/items",
            items=uris,
            chunk_field_name="uris",
            chunk_size=100
        )

    async def _delete_tracks_from_playlist(self, playlist_id: str, uris: list[dict[str, str]]) -> None:
        # uris param format: `[{ "uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh" },{ "uri": "spotify:track:1301WleyT98MSxVHPZCA6M" }]`
        # Spotify API format: `{ "items": [{ "uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh" },{ "uri": "spotify:track:1301WleyT98MSxVHPZCA6M" }] }`
        await self._spotify_session_client.delete_in_chunks(
            endpoint=f"/playlists/{playlist_id}/items",
            items=uris,
            chunk_field_name="items",
            chunk_size=100,
        )
