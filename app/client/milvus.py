"""Milvus connection manager — singleton, lifespan-managed.

Usage:

    # Lifespan startup
    milvus_manager.init(config.milvus)

    # Dependency
    repo = VectorStoreRepository(
        embedding=embedding,
        client=milvus_manager.client,
        aclient=milvus_manager.aclient,
    )

    # Lifespan shutdown
    await milvus_manager.close()
"""

from typing import Optional

from pymilvus import AsyncMilvusClient, MilvusClient

from app.core.config import MilvusConfig


class MilvusManager:
    def __init__(self):
        self.config: Optional[MilvusConfig] = None
        self.client: Optional[MilvusClient] = None
        self.aclient: Optional[AsyncMilvusClient] = None

    def init(self, config: MilvusConfig) -> None:
        self.config = config
        self.client = MilvusClient(
            uri=config.milvus_uri,
            user=config.milvus_user,
            password=config.milvus_password,
            db_name=config.milvus_db,
            timeout=config.milvus_timeout,
        )
        self.aclient = AsyncMilvusClient(
            uri=config.milvus_uri,
            user=config.milvus_user,
            password=config.milvus_password,
            db_name=config.milvus_db,
            timeout=config.milvus_timeout,
        )
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Create the target database if it doesn't exist."""
        admin = MilvusClient(
            uri=self.config.milvus_uri,
            user=self.config.milvus_user,
            password=self.config.milvus_password,
            timeout=self.config.milvus_timeout,
        )
        if self.config.milvus_db not in admin.list_databases():
            admin.create_database(self.config.milvus_db)
        admin.close()

    async def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
        if self.aclient:
            await self.aclient.close()
            self.aclient = None


# Module-level singleton — wired into lifespan.
milvus_manager = MilvusManager()
