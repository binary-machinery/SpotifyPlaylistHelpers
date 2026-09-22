from fastapi import APIRouter

from sph_backend.api import schemas
from sph_backend.api.dependencies import SpotifyServiceDep

router = APIRouter(
    prefix="/playlists",
    tags=["playlists"]
)


@router.get("")
async def get_playlists(spotify_service: SpotifyServiceDep) -> schemas.Page[schemas.SimplifiedPlaylist]:
    playlists = await spotify_service.get_playlists()
    return schemas.Page[schemas.SimplifiedPlaylist](
        total=len(playlists),
        items=[schemas.SimplifiedPlaylist.from_domain(p) for p in playlists]
    )


@router.get("/{playlist_id}/new-releases")
async def get_new_releases_for_playlist(playlist_id: str, spotify_service: SpotifyServiceDep) \
        -> schemas.Page[schemas.ArtistReleases]:
    latest_dates, releases = await spotify_service.get_new_releases_for_playlist(playlist_id)
    return schemas.Page[schemas.ArtistReleases](
        total=sum(len(artist_releases) for artist_releases in releases.values()),
        items=[schemas.ArtistReleases.from_domain(artist, artist_releases)
               for artist, artist_releases in releases.items()]
    )


@router.post("/{playlist_id}/add-artist")
async def add_artist_to_playlist(playlist_id: str, spotify_services: SpotifyServiceDep, artist_id: str) \
        -> schemas.GenericSuccess:
    await spotify_services.add_artist_to_playlist(playlist_id, artist_id)
    return schemas.GenericSuccess()


@router.post("/{playlist_id}/subtract-playlist")
async def subtract_playlist_from_playlist(
        playlist_id: str, spotify_services: SpotifyServiceDep, target_playlist_id: str
) -> schemas.GenericSuccess:
    await spotify_services.subtract_playlist(playlist_id, target_playlist_id)
    return schemas.GenericSuccess()


@router.post("/{playlist_id}/extract-tracks")
async def extract_tracks_from_playlist_by_keyword(
        playlist_id: str, spotify_services: SpotifyServiceDep, keyword: str, result_playlist_id: str | None = None
) -> schemas.GenericSuccess:
    await spotify_services.find_tracks_in_playlist(
        playlist_id=playlist_id,
        keyword=keyword,
        result_playlist_id=result_playlist_id
    )
    return schemas.GenericSuccess()


@router.post("/{playlist_id}/extract-duplicates")
async def extract_duplicates_from_playlist(
        playlist_id: str, spotify_services: SpotifyServiceDep, result_playlist_id: str | None = None
) -> schemas.GenericSuccess:
    await spotify_services.find_duplicates(
        playlist_id=playlist_id,
        result_playlist_id=result_playlist_id
    )
    return schemas.GenericSuccess()
