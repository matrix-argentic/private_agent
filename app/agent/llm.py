from langchain_qwq import ChatQwen
from langchain_openai import ChatOpenAI

from app.core.config import LLMConfig


def get_llm(conf: LLMConfig) -> ChatQwen:
    model = ChatQwen(
        model=conf.dashscope_model,
        max_tokens=3_000,
        timeout=None,
        max_retries=2,
        api_key=conf.dashscope_api_key,
        base_url=conf.dashscope_api_base,
        enable_thinking=False,  # 关闭thinking
        # other params...
    )
    return model
