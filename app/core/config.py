"""App configuration — loads config/app.yaml via OmegaConf.

Usage:
    from app.core.config import get_app_config

    cfg = get_app_config()
    print(cfg.embedding_model)
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from omegaconf import OmegaConf

_APP_YAML = Path(__file__).resolve().parents[2] / "config" / "app.yaml"


@dataclass
class EmbeddingConfig:
    embedding_model: str = "BAAI/bge-m3"
    siliconflow_api_key: str = ""


@dataclass
class MilvusConfig:
    milvus_uri: str = ""
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_db: str = ""
    milvus_timeout: int = 3


@dataclass
class LLMConfig:
    dashscope_api_key: str = ""
    dashscope_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen3.5-flash"
    system_prompt: str = "你是一个专业的 AI 助手。请用中文回答。"


@dataclass
class AuthConfig:
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080


@dataclass
class AppConfig:
    """App configuration schema.

    Defaults are defined here; config/app.yaml can override them;
    ${oc.env:...} placeholders are resolved from .env / environment.
    """

    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    milvus: MilvusConfig = field(default_factory=MilvusConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    knowledge_base_url: str = "https://iknow.lenovo.com.cn/"


@lru_cache
def get_app_config(yaml_path: str | None = None) -> AppConfig:
    """Load YAML, merge with schema defaults, resolve ``${oc.env:...}``."""
    path = Path(yaml_path) if yaml_path else _APP_YAML
    content = OmegaConf.load(path) if path.exists() else OmegaConf.create({})
    schema = OmegaConf.structured(AppConfig)
    return OmegaConf.to_object(OmegaConf.merge(schema, content))
