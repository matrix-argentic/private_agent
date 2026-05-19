"""Tests for agent.config.config — OmegaConf-based agent config loading."""

from pathlib import Path

from app.agent.config.config import (
    AgentAppConfig,
    AgentConfig,
    ServerConfig,
    get_agent_config,
)


# ── Schema types ────────────────────────────────────────────────────────────


def test_agent_config_schema():
    """Verify the schema is constructable with defaults."""
    cfg = AgentAppConfig()
    assert isinstance(cfg.agent, AgentConfig)
    assert isinstance(cfg.server, ServerConfig)
    assert cfg.agent.model == "gpt-4o"
    assert cfg.server.port == 8100


def test_agent_config_defaults():
    cfg = AgentAppConfig()
    assert cfg.agent.model == "gpt-4o"
    assert cfg.agent.temperature == 0.7
    assert cfg.agent.max_tokens == 4096
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 8100


# ── get_agent_config (OmegaConf merge) ─────────────────────────────────────


def test_get_agent_config_type():
    """Returns typed AgentAppConfig, not a raw dict."""
    cfg = get_agent_config()
    assert isinstance(cfg, AgentAppConfig)
    assert isinstance(cfg.agent, AgentConfig)
    assert isinstance(cfg.server, ServerConfig)


def test_get_agent_config_loads_yaml():
    """Reads the real config/agent.yaml and returns agent/server sections."""
    cfg = get_agent_config()
    assert cfg.agent.model == "gpt-4o"
    assert cfg.server.host == "0.0.0.0"


def test_get_agent_config_missing_file(tmp_path):
    """Missing yaml returns all-defaults AgentAppConfig."""
    cfg = get_agent_config(str(tmp_path / "nonexistent.yaml"))
    assert cfg.agent.model == "gpt-4o"
    assert cfg.server.port == 8100


def test_get_agent_config_custom_yaml(tmp_path):
    """A custom YAML file overrides schema defaults."""
    import yaml

    custom = tmp_path / "custom_agent.yaml"
    custom.write_text(
        yaml.dump({"agent": {"model": "custom-model"}}), encoding="utf-8"
    )
    cfg = get_agent_config(str(custom))
    assert cfg.agent.model == "custom-model"
    assert cfg.server.port == 8100  # default preserved
