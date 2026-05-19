from loguru import logger

from app.agent.llm import get_llm
from app.agent.prompts.intent import INTENT_PROMPT
from app.agent.schema import IntentOutput
from app.agent.state import ChatContext, ChatState
from app.core.config import get_app_config
from langgraph.runtime import Runtime
from langgraph.types import Command


def intent_node(state: ChatState, runtime: Runtime[ChatContext]) -> ChatState:
    query = state.get("query", "")

    conf = get_app_config()
    langfuse = runtime.context["langfuse"]
    requestion_prompt_client = langfuse.get_prompt(
        "intent_prompt", label="latest", fallback=INTENT_PROMPT
    )

    knowledge_repo = runtime.context["knowledge_repo"]
    kbs = knowledge_repo.list()
    tool_list = []
    kb_list = "\n".join(f"- {kb.id}: {kb.description}" for kb in kbs)
    args = {
        "tool_list": "\n".join(
            f"{tool['name']}: {tool['description']}" for tool in tool_list
        ),
        "kb_list": kb_list,
        "summary": state.get("summary", ""),
        "chat_history": "\n".join(
            f"{msg.type}: {msg.content}" for msg in state.get("messages", [])
        ),
        "user_query": query,
    }
    prompt = requestion_prompt_client.compile(**args)
    llm = get_llm(conf=conf.llm)

    resp = llm.with_structured_output(schema=IntentOutput).invoke(input=prompt)
    intent = resp.intent
    logger.info(
        f"user intent: {intent} (tools={resp.matched_tool_ids}, kbs={resp.matched_kb_ids})"
    )

    """
    - knowledge_qa：查询问题需要检索知识库内容
    - tool_call：需要调用上方列表中的某个工具
    - chat：闲聊、个人偏好、生活、情绪、日常交流
    - command：总结、翻译、改写、生成文案等通用指令
    - invalid：无意义、乱码、无法识别、敏感内容
    """
    if intent == "knowledge_qa":
        return Command(
            update={
                "intent": intent,
                "matched_kb_ids": resp.matched_kb_ids,
            },
            goto="requestion_node",
        )
    else:
        return Command(
            update={
                "intent": intent,
                "re_query": query,
                "matched_tool_ids": resp.matched_tool_ids,
            },
            goto="chat_node",
        )
