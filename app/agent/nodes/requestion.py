from langgraph.runtime import Runtime
from loguru import logger

from app.agent.llm import get_llm
from app.agent.prompts.requestion import REQUESTION_PROMPT
from app.agent.state import ChatContext, ChatState
from app.core.config import get_app_config


def requestion_node(state: ChatState, runtime: Runtime[ChatContext]) -> ChatState:
    # 这里可以添加一些预处理逻辑，比如敏感词过滤、输入校验等

    query = state.get("query", "")

    conf = get_app_config()
    langfuse = runtime.context["langfuse"]
    requestion_prompt_client = langfuse.get_prompt(
        "requestion_prompt", label="latest", fallback=REQUESTION_PROMPT
    )
    args = {
        "summary": state.get("summary", ""),
        "chat_history": "\n".join(
            f"{msg.type}: {msg.content}" for msg in state.get("messages", [])
        ),
        "user_query": query,
    }
    prompt = requestion_prompt_client.compile(**args)
    llm = get_llm(conf=conf.llm)

    resp = llm.invoke(input=prompt)
    # writer = runtime.stream_writer
    re_query = resp.content.strip() if resp.content else ""

    logger.info(f"Original query: {query}")
    logger.info(f"Rewritten query: {re_query}")

    if not re_query:
        logger.info(f"Using original query: {query}")
        return {"re_query": query}
    return {"re_query": re_query}
