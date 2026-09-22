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


@router.get("/{playlist_id}/releases")
async def get_new_releases_for_playlist(playlist_id: str, spotify_service: SpotifyServiceDep) \
        -> schemas.Page[schemas.ArtistReleases]:
    latest_dates, releases = await spotify_service.get_new_releases_for_playlist(playlist_id)
    return schemas.Page[schemas.ArtistReleases](
        total=sum(len(artist_releases) for artist_releases in releases.values()),
        items=[schemas.ArtistReleases.from_domain(artist, artist_releases)
               for artist, artist_releases in releases.items()]
    )
