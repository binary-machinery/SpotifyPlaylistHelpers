from fastapi import APIRouter

from sph_backend.api import schemas

router = APIRouter(
    tags=["misc"]
)


@router.get("/health")
async def health() -> schemas.Health:
    return schemas.Health(status="ok")
