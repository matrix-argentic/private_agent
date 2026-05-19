"""Tests for rag.config.config — OmegaConf-based RAG config loading."""

from pathlib import Path

import pytest

from app.core.config import AppConfig, get_app_config

# ── Schema types ────────────────────────────────────────────────────────────


def test_rag_config_schema():
    """Verify the schema is constructable with defaults."""
    cfg = AppConfig()
    assert cfg.embedding.embedding_model == "BAAI/bge-m3"
    assert cfg.embedding.siliconflow_api_key == ""
    assert cfg.llm.dashscope_api_key == ""
    assert (
        cfg.llm.dashscope_api_base
        == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    assert cfg.llm.dashscope_model == "qwen3.5-flash"
    assert cfg.knowledge_base_url == "https://iknow.lenovo.com.cn/"


# ── get_rag_config (OmegaConf merge) ───────────────────────────────────────


def test_get_rag_config_type():
    """Returns typed RagConfig, not a raw dict."""
    cfg = get_app_config()
    assert isinstance(cfg, AppConfig)


def test_get_rag_config_loads_yaml():
    """Reads the real config/rag.yaml and returns expected fields."""
    cfg = get_app_config()
    assert cfg.embedding.embedding_model is not None
    assert cfg.embedding.embedding_model == "BAAI/bge-m3"


def test_get_rag_config_env_overrides(monkeypatch):
    """Env var EMBEDDING_MODEL overrides the ${oc.env:...} default in YAML."""
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    cfg = get_app_config()
    assert cfg.embedding.embedding_model == "text-embedding-3-large"


def test_get_rag_config_missing_file(tmp_path):
    """Missing yaml file returns all-defaults RagConfig."""
    cfg = get_app_config(str(tmp_path / "nonexistent.yaml"))
    assert cfg.embedding.embedding_model == "BAAI/bge-m3"


def test_get_rag_config_custom_yaml(tmp_path):
    """A custom YAML file overrides schema defaults."""
    import yaml

    custom = tmp_path / "custom_rag.yaml"
    custom.write_text(
        yaml.dump({"embedding": {"embedding_model": "custom-model"}}),
        encoding="utf-8",
    )
    cfg = get_app_config(str(custom))
    assert cfg.embedding.embedding_model == "custom-model"


def test_rag_config_env_fallback():
    """Default without .env is the schema default."""
    cfg = get_app_config()
    assert cfg.embedding.embedding_model == "BAAI/bge-m3"
