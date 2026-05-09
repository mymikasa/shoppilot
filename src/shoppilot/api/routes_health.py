from fastapi import APIRouter, Depends

from shoppilot.api.deps import get_redis
from shoppilot.api.schemas import HealthResponse
from shoppilot.rag.store import get_vectorstore

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def healthz(redis=Depends(get_redis)) -> HealthResponse:
    redis_status = "ok"
    try:
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        redis_status = f"down: {exc.__class__.__name__}"

    chroma_status = "ok"
    chroma_docs = 0
    try:
        store = get_vectorstore()
        chroma_docs = store._collection.count()
        if chroma_docs == 0:
            chroma_status = "empty"
    except Exception as exc:  # noqa: BLE001
        chroma_status = f"down: {exc.__class__.__name__}"

    overall = "ok" if redis_status == "ok" and chroma_status in ("ok", "empty") else "degraded"
    return HealthResponse(
        status=overall,
        redis=redis_status,
        chroma=chroma_status,
        chroma_docs=chroma_docs,
    )
