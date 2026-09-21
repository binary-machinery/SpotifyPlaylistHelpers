from fastapi import APIRouter

from sph_backend.api.dependencies import SpotifyServiceDep

router = APIRouter(
    prefix="/playlists",
    tags=["playlists"]
)


@router.get("/playlists")
async def get_playlists(spotify_service: SpotifyServiceDep):
    playlists = await spotify_service.get_playlists()
    return {"playlists": playlists}
