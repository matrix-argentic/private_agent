"""Embedding implementation — SiliconFlow-compatible API.

Usage:
    embedder = SiliconFlowEmbedding()

    # Sync
    vec = embedder.embed("hello")
    vecs = embedder.embed_batch(["hello", "world"])

    # Async
    vec = await embedder.aembed("hello")
    vecs = await embedder.aembed_batch(["hello", "world"])
"""

import asyncio
import os
from typing import Any, Optional

import httpx
from loguru import logger

from langchain_core.embeddings import Embeddings


class SiliconFlowEmbedding(Embeddings):
    """Embedding via SiliconFlow OpenAI-compatible API.

    Requires ``SILICONFLOW_API_KEY`` env var (or pass ``api_key``).

    Supports both sync (:meth:`embed`, :meth:`embed_batch`) and
    async (:meth:`aembed`, :meth:`aembed_batch`) usage.

    HTTP clients are created lazily and should be closed after use::

        embedder = SiliconFlowEmbedding()
        ...
        embedder.close()          # sync
        await embedder.aclose()   # async
    """

    def __init__(
        self,
        model: str = "BAAI/bge-m3",
        api_url: str = "https://api.siliconflow.cn/v1/embeddings",
        api_key: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
        max_retries: int = 3,
        batch_size: int = 32,
    ):
        self.model = model
        self.api_url = api_url
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SILICONFLOW_API_KEY is not set — pass api_key or set the env var"
            )
        self.max_retries = max_retries
        self._timeout = timeout or httpx.Timeout(
            connect=5.0, read=30.0, write=10.0, pool=5.0
        )
        self._batch_size = batch_size

        # Lazily created clients
        self._async_client: httpx.AsyncClient | None = None
        self._sync_client: httpx.Client | None = None

    # ── Client lifecycle ──────────────────────────────────────────────────────

    @property
    def _aclient(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._async_client

    @property
    def _sclient(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._sync_client

    async def aclose(self) -> None:
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def close(self) -> None:
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None

    # ── Context manager support ────────────────────────────────────────────────

    async def __aenter__(self) -> "SiliconFlowEmbedding":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
        self.close()

    def __enter__(self) -> "SiliconFlowEmbedding":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Internal request helpers with retry ────────────────────────────────────

    async def _request(self, input_data: str | list[str]) -> dict[str, Any]:
        """POST embedding request with retry + exponential backoff.

        ``input_data`` is passed directly as the ``input`` field so that
        the caller controls single-string vs batch-array mode.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._aclient.post(
                    self.api_url,
                    json={"input": input_data, "model": self.model},
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "embed timeout (attempt {}/{}): {}", attempt, self.max_retries, exc
                )
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                body = exc.response.text[:200]
                logger.warning(
                    "embed HTTP {} (attempt {}/{}): {}",
                    exc.response.status_code,
                    attempt,
                    self.max_retries,
                    body,
                )
                # 4xx that aren't 429 are not retryable
                if (
                    400 <= exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
            if attempt < self.max_retries:
                wait = 2**attempt  # 2, 4, 8 s
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"embedding failed after {self.max_retries} retries"
        ) from last_exc

    def _sync_request(self, input_data: str | list[str]) -> dict[str, Any]:
        """Sync counterpart of :meth:`_request`."""
        last_exc: Exception | None = None
        import time

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._sclient.post(
                    self.api_url,
                    json={"input": input_data, "model": self.model},
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "embed timeout (attempt {}/{}): {}", attempt, self.max_retries, exc
                )
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                body = exc.response.text[:200]
                logger.warning(
                    "embed HTTP {} (attempt {}/{}): {}",
                    exc.response.status_code,
                    attempt,
                    self.max_retries,
                    body,
                )
                if (
                    400 <= exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
            if attempt < self.max_retries:
                wait = 2**attempt
                time.sleep(wait)

        raise RuntimeError(
            f"embedding failed after {self.max_retries} retries"
        ) from last_exc

    # ── Async public API ──────────────────────────────────────────────────────

    async def aembed_query(self, text: str) -> list[float]:
        """Embed a single text asynchronously."""
        logger.debug("aembed: text={}", text[:80])
        data = await self._request(text)
        return data["data"][0]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts asynchronously in a single request per chunk."""
        logger.info("aembed_batch: count={}", len(texts))
        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            data = await self._request(chunk)
            # Responses are ordered by index; sort to be defensive
            vectors = [
                item["embedding"]
                for item in sorted(data["data"], key=lambda x: x["index"])
            ]
            all_vectors.extend(vectors)
        return all_vectors

    # ── Sync public API ───────────────────────────────────────────────────────

    def embed_query(self, text: str) -> list[float]:
        """Embed a single text synchronously."""
        logger.debug("embed: text={}", text[:80])
        data = self._sync_request(text)
        return data["data"][0]["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts synchronously in a single request per chunk."""
        logger.info("embed_batch: count={}", len(texts))
        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            data = self._sync_request(chunk)
            vectors = [
                item["embedding"]
                for item in sorted(data["data"], key=lambda x: x["index"])
            ]
            all_vectors.extend(vectors)
        return all_vectors
