"""Tests for SiliconFlowEmbedding — mock transport, no real HTTP calls."""

import json

import httpx
import pytest
from httpx import MockTransport

from app.pkg.embedding.silicon_flow import SiliconFlowEmbedding

# ── Helpers ──────────────────────────────────────────────────────────────────

SAMPLE_EMBEDDING = [0.0123, -0.0456, 0.0789]
SAMPLE_RESPONSE = {
    "data": [{"embedding": SAMPLE_EMBEDDING, "index": 0}],
    "model": "BAAI/bge-m3",
    "usage": {"total_tokens": 1},
}
BATCH_RESPONSE = {
    "data": [
        {"embedding": [0.1, 0.2], "index": 0},
        {"embedding": [0.3, 0.4], "index": 1},
    ],
    "model": "BAAI/bge-m3",
    "usage": {"total_tokens": 2},
}


def _inject_async_client(embedder: SiliconFlowEmbedding, handler):
    """Replace the embedder's lazy async client with a MockTransport-backed one."""
    embedder._async_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {embedder.api_key}"},
        transport=MockTransport(handler),
    )


def _inject_sync_client(embedder: SiliconFlowEmbedding, handler):
    """Replace the embedder's lazy sync client with a MockTransport-backed one."""
    embedder._sync_client = httpx.Client(
        headers={"Authorization": f"Bearer {embedder.api_key}"},
        transport=MockTransport(handler),
    )


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def embedder():
    return SiliconFlowEmbedding(api_key="test-key")


# ── Async: aembed ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_aembed_success(embedder):
    """
    正常请求，验证 auth header、请求体、返回值
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["input"] == "hello"
        assert body["model"] == "BAAI/bge-m3"
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    _inject_async_client(embedder, handler)
    vec = await embedder.aembed_query("hello")
    assert vec == SAMPLE_EMBEDDING


@pytest.mark.anyio
async def test_aembed_retry_on_timeout_then_succeeds(embedder):
    """
    第一次超时，重试后成功
    """
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ReadTimeout("first attempt timed out")
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    _inject_async_client(embedder, handler)
    vec = await embedder.aembed_query("hello")
    assert vec == SAMPLE_EMBEDDING
    assert call_count == 2


@pytest.mark.anyio
async def test_aembed_raises_on_non_retryable_4xx(embedder):
    """
    400 不重试，直接抛异常
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    _inject_async_client(embedder, handler)
    with pytest.raises(RuntimeError, match="failed after"):
        await embedder.aembed_query("hello")


@pytest.mark.anyio
async def test_aembed_retries_on_5xx(embedder):
    """
    500 重试耗尽后抛异常
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal error"})

    _inject_async_client(embedder, handler)
    with pytest.raises(RuntimeError, match="failed after"):
        await embedder.aembed_query("hello")


# ── Async: aembed_batch ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_aembed_batch_success(embedder):
    """
    批量请求，验证排序
    """

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["input"] == ["hello", "world"]
        return httpx.Response(200, json=BATCH_RESPONSE)

    _inject_async_client(embedder, handler)
    vecs = await embedder.aembed_documents(["hello", "world"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.anyio
async def test_aembed_batch_empty(embedder):
    """
    空列表返回空
    """
    vecs = await embedder.aembed_documents([])
    assert vecs == []


@pytest.mark.anyio
async def test_aembed_batch_chunks(embedder):
    """
    分块逻辑（batch_size=2 → 3 条数据分 2 次请求）
    """
    embedder._batch_size = 2
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        body = json.loads(request.content)
        if call_count == 1:
            assert body["input"] == ["a", "b"]
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"embedding": [0.1], "index": 0},
                        {"embedding": [0.2], "index": 1},
                    ]
                },
            )
        assert body["input"] == ["c"]
        return httpx.Response(200, json={"data": [{"embedding": [0.3], "index": 0}]})

    _inject_async_client(embedder, handler)
    vecs = await embedder.aembed_documents(["a", "b", "c"])
    assert vecs == [[0.1], [0.2], [0.3]]
    assert call_count == 2


# ── Sync: embed ──────────────────────────────────────────────────────────────


def test_embed_success(embedder):
    """
    同步正常请求
    """

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["input"] == "hello"
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    _inject_sync_client(embedder, handler)
    vec = embedder.embed_query("hello")
    assert vec == SAMPLE_EMBEDDING


def test_embed_retry_on_timeout_then_succeeds(embedder):
    """
    同步重试
    """
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ReadTimeout("first attempt timed out")
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    _inject_sync_client(embedder, handler)
    vec = embedder.embed_query("hello")
    assert vec == SAMPLE_EMBEDDING
    assert call_count == 2


# ── Sync: embed_batch ────────────────────────────────────────────────────────


def test_embed_batch_success(embedder):
    """
    同步批量
    """

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["input"] == ["hello", "world"]
        return httpx.Response(200, json=BATCH_RESPONSE)

    _inject_sync_client(embedder, handler)
    vecs = embedder.embed_documents(["hello", "world"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_batch_empty(embedder):
    """
    同步空列表
    """
    vecs = embedder.embed_documents([])
    assert vecs == []


# ── Initialisation ───────────────────────────────────────────────────────────


def test_missing_api_key_raises(monkeypatch):
    """
    无 key 抛 ValueError
    """
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SILICONFLOW_API_KEY"):
        SiliconFlowEmbedding(api_key="")


def test_default_model():
    """
    默认 model 正确
    """
    e = SiliconFlowEmbedding(api_key="test-key")
    assert e.model == "BAAI/bge-m3"


# ── Context manager ──────────────────────────────────────────────────────────


def test_sync_context_manager(embedder):
    """
    with 不抛异常
    """
    with embedder:
        pass  # no exception = client is usable


@pytest.mark.anyio
async def test_async_context_manager(embedder):
    """
    async with 不抛异常
    """
    async with embedder:
        pass  # no exception = client is usable
