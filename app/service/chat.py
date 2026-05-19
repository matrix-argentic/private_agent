import asyncio
import json
import uuid
from datetime import datetime, timezone

from langchain.messages import HumanMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from loguru import logger

from app.agent.llm import get_llm
from app.agent.prompts.summary import SUMMARY_PROMPT
from app.agent.state import ChatContext
from app.core.config import get_app_config
from app.repository.chat_message import ChatMessageRepository
from app.repository.document import DocumentRepository
from app.repository.knowledge import KnowledgeRepository
from app.server.models.chat_message import ChatMessageModel
from app.service.search import SearchService


class ChatService:

    def __init__(
        self,
        agent: CompiledStateGraph,
        langfuse: Langfuse,
        langfuse_handler: CallbackHandler,
        document_repo: DocumentRepository,
        knowledge_repo: KnowledgeRepository,
        search_service: SearchService,
        chat_message_repo: ChatMessageRepository,
    ):
        self._agent = agent
        self._langfuse = langfuse
        self._langfuse_handler = langfuse_handler
        self._document_repo = document_repo
        self._knowledge_repo = knowledge_repo
        self._search_service = search_service
        self._chat_message_repo = chat_message_repo

    async def chat(self, query: str):
        session_id = "user123_session1"
        user_id = "user123"
        config = RunnableConfig(
            configurable={"thread_id": session_id, "user_id": user_id},
            callbacks=[self._langfuse_handler],
        )
        metadata = {
            "thread_id": session_id,
            "user": "zhangsan",
            "user_id": user_id,
            "level": 1,
        }
        input = {"query": query}
        context = ChatContext(
            langfuse=self._langfuse,
            document_repo=self._document_repo,
            knowledge_repo=self._knowledge_repo,
            search_service=self._search_service,
        )
        try:

            with propagate_attributes(session_id=session_id, user_id=user_id):
                with self._langfuse.start_as_current_observation(
                    as_type="generation",
                    name="chat",
                    level="DEFAULT",
                    metadata=metadata,
                    input=input,
                ) as graph_generation:
                    graph_generation.update(input=input)
                    async for type, chunk in self._agent.astream(
                        input=input,
                        config=config,
                        stream_mode=["custom"],
                        context=context,
                    ):
                        if type == "custom":
                            if content := (chunk or ""):
                                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                    state_snap = await self._agent.aget_state(config)
                    message = state_snap.values.get("messages", [])[-1]
                    response_content = (
                        message.content if hasattr(message, "content") else str(message)
                    )
                    graph_generation.update(output=message)

                    # 流式结束，异步保存聊天记录 + 执行 summary
                    asyncio.create_task(
                        self._background_save_chat(
                            session_id=session_id,
                            user_id=user_id,
                            query=query,
                            response=response_content,
                        )
                    )
                    asyncio.create_task(self._background_summary(config))
        except Exception as exc:
            logger.error("Chat stream error: {}", exc)
            asyncio.create_task(
                self._background_save_chat(
                    session_id=session_id,
                    user_id=user_id,
                    query=query,
                    response="",
                    error=str(exc),
                )
            )
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    def get_chat_history(
        self,
        session_id: str = "user123_session1",
        before_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        """获取指定会话的历史聊天记录，按时间倒序返回。"""
        records = self._chat_message_repo.list_before(
            session_id=session_id, before_id=before_id, limit=limit
        )
        has_more = len(records) > limit
        if has_more:
            records = records[:-1]
        return {
            "messages": [
                {
                    "id": r.id,
                    "query": r.query,
                    "response": r.response,
                    "created_at": r.created_at,
                    "rating": r.rating,
                    "comment": r.comment,
                    "error": r.error,
                }
                for r in records
            ],
            "has_more": has_more,
        }

    async def _background_save_chat(
        self,
        session_id: str,
        user_id: str,
        query: str,
        response: str,
        error: str | None = None,
    ) -> None:
        """异步保存本轮聊天记录到数据库。"""
        try:
            model = ChatMessageModel(
                id=uuid.uuid4().hex,
                session_id=session_id,
                user_id=user_id,
                query=query,
                response=response,
                created_at=datetime.now(timezone.utc).isoformat(),
                error=error,
            )
            self._chat_message_repo.create(model)
            logger.debug("Chat message saved: {} ({})", model.id, session_id)
        except Exception as e:
            logger.error("Failed to save chat message: {}", e)

    async def _background_summary(self, config: RunnableConfig) -> None:
        """检查是否需要 summary，需要则异步执行并更新 checkpoint 状态。"""
        try:
            state = await self._agent.aget_state(config)
            if state is None:
                return

            messages = state.values.get("messages", [])
            # 超过 15 轮（30 条消息）才做 summary
            # if len(messages) < 30:
            # TODO: 测试而已，4轮总结最早的3轮，剩余1轮，生产环境可以 15轮总结 12轮，剩余最近的3轮
            if len(messages) < 8:
                return

            summary = state.values.get("summary")

            client = self._langfuse.get_prompt(
                "summary_prompt",
                label="latest",
                fallback=SUMMARY_PROMPT,
            )
            args = {
                "old_summary": summary,
                "new_messages": "\n".join(
                    f"{msg.type}: {msg.content}"
                    for msg in messages[:-2]  # TODO: 剩下最后一轮
                ),
                "max_tokens": 500,  # TODO: 生产环境可以 1000-2000 字左右
            }
            prompt = client.compile(**args)
            llm = get_llm(conf=get_app_config().llm)
            # 还需要剩下最近2轮
            result = await llm.ainvoke(input=prompt)

            # TODO: 剩下最后一轮
            delete_messages = [RemoveMessage(id=m.id) for m in messages[:-2]]

            await self._agent.aupdate_state(
                config,
                {"summary": result.content, "messages": delete_messages},
            )
            logger.info(
                "Background summary done, {} messages archived", len(delete_messages)
            )
            logger.info(f"Summary content: {result.content}")

        except Exception as e:
            logger.error("Background summary failed: {}", e)
