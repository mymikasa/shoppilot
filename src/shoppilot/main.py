import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shoppilot.agent.checkpointer import make_checkpointer
from shoppilot.agent.graph import build_graph
from shoppilot.agent.llm import build_llm
from shoppilot.api.routes_chat import router as chat_router
from shoppilot.api.routes_health import router as health_router
from shoppilot.api.routes_session import router as session_router
from shoppilot.config import get_settings
from shoppilot.persistence.redis_client import make_redis

logger = logging.getLogger("shoppilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("shoppilot starting up")

    redis = make_redis(settings.redis_url)
    checkpointer, checkpointer_redis = await make_checkpointer(settings.redis_url)
    llm = build_llm()
    graph = build_graph(checkpointer=checkpointer, llm=llm)

    app.state.redis = redis
    app.state.checkpointer = checkpointer
    app.state.checkpointer_redis = checkpointer_redis
    app.state.graph = graph
    logger.info("shoppilot ready")

    try:
        yield
    finally:
        await redis.aclose()
        await checkpointer_redis.aclose()
        logger.info("shoppilot shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ShopPilot",
        version="0.1.0",
        description="电商智能客服 Agent",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(session_router)
    return app


app = create_app()
