from __future__ import annotations

from pathlib import Path

import aiosqlite
from langgraph.graph import START, END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

from app.agent.nodes.chat import chat_node
from app.agent.nodes.intent import intent_node
from app.agent.nodes.requestion import requestion_node
from app.agent.nodes.retrieve import retrieve_node
from app.agent.state import ChatContext, ChatState

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "database" / "agent.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_agent: CompiledStateGraph | None = None
_agent_conn: aiosqlite.Connection | None = None
_store_conn: aiosqlite.Connection | None = None


async def get_agent():
    """Get or create the compiled agent (lazy, async init)."""
    global _agent, _agent_conn, _store_conn
    if _agent is not None:
        return _agent

    builder = StateGraph(
        state_schema=ChatState,
        context_schema=ChatContext,
    )

    builder.add_node("intent_node", intent_node)
    builder.add_node("requestion_node", requestion_node)
    builder.add_node("retrieve_node", retrieve_node)
    builder.add_node("chat_node", chat_node)

    builder.add_edge(START, "intent_node")
    builder.add_edge("requestion_node", "retrieve_node")
    builder.add_edge("retrieve_node", "chat_node")
    builder.add_edge("chat_node", END)

    _agent_conn = await aiosqlite.connect(str(_DB_PATH))
    _store_conn = await aiosqlite.connect(str(_DB_PATH))
    checkpointer = AsyncSqliteSaver(_agent_conn)
    store = AsyncSqliteStore(_store_conn)

    _agent = builder.compile(
        checkpointer=checkpointer,
        store=store,
    )
    return _agent


async def close_agent():
    """Close the agent's SQLite connections (call during lifespan shutdown)."""
    global _agent, _agent_conn, _store_conn
    _agent = None
    if _agent_conn is not None:
        await _agent_conn.close()
        _agent_conn = None
    if _store_conn is not None:
        await _store_conn.close()
        _store_conn = None


if __name__ == "__main__":
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler
    from langchain_core.runnables.config import RunnableConfig
    import asyncio
    from uuid import uuid4

    agent = asyncio.run(get_agent())

    # TODO: mock session_id
    langfuse = get_client()
    langfuse_handler = CallbackHandler()
    session_id = str(uuid4())
    result = agent.invoke(
        input={"query": "你好"},
        config=RunnableConfig(
            callbacks=[langfuse_handler],
            configurable={
                "thread_id": session_id,
            },
            metadata={"langfuse_tags": ["simple_call"]},  # tags
        ),
        context=ChatContext(
            langfuse=langfuse,
            search_service=None,  # type: ignore[assignment]
        ),
    )
    print(result)

    langfuse.flush()
