from fastapi import Depends, HTTPException

from app.server.dependency.dependency import get_knowledge_service
from app.server.router.router import protected_router

from app.server.schema.knowledge import (
    CreateKnowledgeRequest,
    UpdateKnowledgeRequest,
)

from app.service.knowledge import KnowledgeService


@protected_router.get("/knowledges")
def list_knowledge_bases(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """获取所有知识库分组"""
    return knowledge_service.list()


@protected_router.post("/knowledges", status_code=201)
def create_knowledge_base(
    req: CreateKnowledgeRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """创建知识库分组"""
    return knowledge_service.create(req)


@protected_router.delete("/knowledges/{kb_id}")
def delete_knowledge_base(
    kb_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """删除知识库分组"""
    knowledge_service.delete(kb_id)
    return {"message": "ok"}


@protected_router.patch("/knowledges/{kb_id}")
def update_knowledge_base(
    kb_id: str,
    req: UpdateKnowledgeRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """更新知识库名称或描述"""
    updated = knowledge_service.update(kb_id, name=req.name, description=req.description)
    if not updated:
        raise HTTPException(404, f"knowledge base '{kb_id}' not found")
    return updated
