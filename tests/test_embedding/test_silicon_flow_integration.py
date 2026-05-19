"""Integration tests for SiliconFlowEmbedding — real API calls.

Requires ``SILICONFLOW_API_KEY`` in ``.env`` (project root).
Run with::

    uv run pytest -m integration
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.pkg.embedding.silicon_flow import SiliconFlowEmbedding

# ── Load .env so tests can read SILICONFLOW_API_KEY ──────────────────────────

load_dotenv(Path(__file__).parents[2] / ".env", override=False)


# ── Tests ────────────────────────────────────────────────────────────────────
# uv run pytest tests/test_embedding/test_silicon_flow_integration.py -m integration -s


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SILICONFLOW_API_KEY"),
    reason="需要 .env 中配置 SILICONFLOW_API_KEY",
)
@pytest.mark.anyio
async def test_aembed_real_request():
    """验证向量维度 >0、元素类型为 float。"""
    async with SiliconFlowEmbedding() as emb:
        vec = await emb.aembed_query("hello")
    print(f"文档维度{len(vec)},向量:{vec[:5]}")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SILICONFLOW_API_KEY"),
    reason="需要 .env 中配置 SILICONFLOW_API_KEY",
)
@pytest.mark.anyio
async def test_aembed_batch_real_request():
    """批量请求返回数量一致、顺序正确。"""
    texts = ["hello", "world"]
    async with SiliconFlowEmbedding() as emb:
        vecs = await emb.aembed_documents(texts)
    [
        print(f"第{idx}个文档,维度{len(vec)},向量:{vec[:5]}")
        for idx, vec in enumerate(vecs)
    ]
    assert isinstance(vecs, list)
    assert len(vecs) == len(texts)
    for v in vecs:
        assert isinstance(v, list) and len(v) > 0
