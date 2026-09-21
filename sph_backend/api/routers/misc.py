from fastapi import APIRouter

router = APIRouter(
    tags=["misc"]
)


@router.get("/health")
async def health():
    return {"status": "ok"}
