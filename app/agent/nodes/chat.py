from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from loguru import logger

from app.agent.llm import get_llm
from app.agent.prompts.agent import AGENT_PROMPT
from app.agent.state import ChatContext, ChatState
from app.core.config import get_app_config


async def chat_node(state: ChatState, runtime: Runtime[ChatContext]) -> ChatState:
    conf = get_app_config()
    llm = get_llm(conf=conf.llm)
    writer = runtime.stream_writer
    retrieved_docs = state.get("retrieved_docs", [])

    query = state.get("re_query", "")
    origin_query = query
    if retrieved_docs:
        context = "\n\n".join(doc["content"] for doc in retrieved_docs)
        query = f"""请根据以下检索到的上下文内容回答用户问题。
如果上下文不足以回答问题，请基于你自己的知识回答。

检索到的上下文：
{context}

用户问题：{query}"""

    langfuse = runtime.context["langfuse"]
    agent_prompt_client = langfuse.get_prompt(
        "agent_prompt", label="latest", fallback=AGENT_PROMPT
    )

    system_message = SystemMessage(content=agent_prompt_client.prompt)
    human_message = HumanMessage(content=query)
    origin_human_message = HumanMessage(content=origin_query)

    # 如果有 summary（历史总结），放在 system 之后、messages 之前
    summary_content = state.get("summary")
    summary_message = (
        [
            SystemMessage(
                content=f"以下是你们之前的对话总结，请基于此保持对话连贯：\n{summary_content}"
            )
        ]
        if summary_content
        else []
    )
    current_messages = (
        [system_message]
        + summary_message
        + (state.get("messages") or [])
        + [human_message]
    )
    full_content = ""
    async for chunk in llm.astream(input=current_messages):
        content = chunk.content or ""
        full_content += content
        writer(content)
    logger.info(f"human message: {human_message.content}")
    logger.info(f"ai message: {full_content}")
    if full_content:
        ai_message = AIMessage(content=full_content)
        # 这里直接返回完整消息列表，实际可以只返回增量消息，前端合并展示
        return {"messages": [origin_human_message, ai_message], "answer": full_content}
    return {"answer": "未知错误"}
