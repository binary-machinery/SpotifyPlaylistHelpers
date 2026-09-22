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
