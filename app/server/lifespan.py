from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import get_client

from app.agent.graph import close_agent
from app.client.milvus import milvus_manager
from app.core.config import get_app_config
from app.client.database import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    db_manager.init()

    config = get_app_config()
    if not config.auth.jwt_secret:
        logger.warning("JWT_SECRET 未设置，身份验证将不可用！请在 .env 中配置 JWT_SECRET")
    if config.milvus.milvus_uri:
        milvus_manager.init(config.milvus)

    yield

    # ── Shutdown ──────────────────────────────────────────────────
    await milvus_manager.close()
    db_manager.close()
    await close_agent()
    get_client().shutdown()
