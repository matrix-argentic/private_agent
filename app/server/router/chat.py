from fastapi import Body, Depends
from fastapi.responses import StreamingResponse

from app.server.dependency.dependency import get_chat_service
from app.server.router.router import protected_router
from app.service.chat import ChatService


@protected_router.get("/chat/history")
def chat_history(
    before_id: str | None = None,
    limit: int = 20,
    chat_service: ChatService = Depends(get_chat_service),
):
    """获取聊天历史记录，支持 cursor 分页。"""
    return chat_service.get_chat_history(before_id=before_id, limit=limit)


@protected_router.post("/agent/chat")
async def agent_chat(
    query: str = Body(..., embed=True),
    chat_service: ChatService = Depends(get_chat_service),
):
    """流式对话接口，返回 SSE 事件流。"""
    # conf = get_app_config()

    # Stream agent response via SSE
    # async def event_stream():
    #     try:
    #         langgraph_config = {"configurable": {"thread_id": "user123_session1"}}
    #         input = {
    #             "query": query,
    #             "messages": [SystemMessage(content=conf.llm.system_prompt)],
    #         }
    #         agent = await get_agent()
    #         async for chunk, _ in agent.astream(
    #             input=input,
    #             config=langgraph_config,
    #             stream_mode="messages",
    #         ):
    #             if not isinstance(chunk, AIMessageChunk):
    #                 continue
    #             if chunk.content:
    #                 yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
    #     except Exception as exc:
    #         logger.error("Chat stream error: {}", exc)
    #         yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
    #     finally:
    #         yield "data: [DONE]\n\n"

    resp = chat_service.chat(query=query)

    return StreamingResponse(
        resp,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
