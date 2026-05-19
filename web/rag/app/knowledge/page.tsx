"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase,
  updateKnowledgeBase,
  type KnowledgeBase,
} from "@/lib/api";
import DocumentList from "./_components/DocumentList";

export default function KnowledgeBasesPage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [docRefreshKey, setDocRefreshKey] = useState(0);
  const [kbFilter, setKbFilter] = useState("");
  const [editKb, setEditKb] = useState<KnowledgeBase | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const fetch = useCallback(async () => {
    try {
      const data = await listKnowledgeBases();
      setKbs(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listKnowledgeBases()
      .then((data) => {
        if (cancelled) return;
        setKbs(data);
        setError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await createKnowledgeBase(newName.trim(), newDesc.trim());
      setNewName("");
      setNewDesc("");
      setShowCreate(false);
      await fetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除知识库「${name}」吗？`)) return;
    try {
      await deleteKnowledgeBase(id);
      if (kbFilter === id) setKbFilter("");
      await fetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  const openEditModal = (kb: KnowledgeBase) => {
    setEditKb(kb);
    setEditName(kb.name);
    setEditDesc(kb.description);
  };

  const closeEditModal = () => {
    setEditKb(null);
    setEditName("");
    setEditDesc("");
  };

  const handleEditSave = async () => {
    if (!editKb || !editName.trim()) return;
    try {
      await updateKnowledgeBase(editKb.id, {
        name: editName.trim(),
        description: editDesc.trim(),
      });
      closeEditModal();
      await fetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <div>
          <h2 className="text-sm font-semibold">知识库管理</h2>
          <p className="text-xs text-zinc-500">创建和管理知识库分组</p>
        </div>
        <button
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          onClick={() => setShowCreate(true)}
        >
          + 新建
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>关闭</button>
        </div>
      )}

      {/* Create form inline */}
      {showCreate && (
        <div className="mx-6 mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <div className="space-y-3">
            <input
              className="w-full rounded-lg border border-blue-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-blue-600 dark:bg-zinc-800"
              placeholder="知识库名称"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              autoFocus
              onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
            />
            <input
              className="w-full rounded-lg border border-blue-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-blue-600 dark:bg-zinc-800"
              placeholder="描述（可选）"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={handleCreate}
                disabled={!newName.trim()}
              >
                创建
              </button>
              <button
                className="rounded-lg bg-zinc-100 px-3 py-1.5 text-sm font-medium hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                onClick={() => { setShowCreate(false); setNewName(""); setNewDesc(""); }}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-500" />
          </div>
        ) : kbs.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <p className="text-sm text-zinc-400">暂无知识库，点击上方「新建」创建</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 pb-6 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {kbs.map((kb) => {
              const isSelected = kbFilter === kb.id;
              return (
              <div
                key={kb.id}
                className={`group cursor-pointer rounded-xl border p-4 transition-colors ${
                  isSelected
                    ? "border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-950"
                    : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-700 dark:hover:border-zinc-600"
                }`}
                onClick={() => setKbFilter(isSelected ? "" : kb.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <h3 className={`truncate text-sm font-semibold ${isSelected ? "text-blue-700 dark:text-blue-300" : ""}`}>
                      {kb.name}
                      {isSelected && <span className="ml-1.5 text-xs text-blue-500">✓</span>}
                    </h3>
                    {kb.description && (
                      <p className="mt-1 text-xs text-zinc-500 line-clamp-2">{kb.description}</p>
                    )}
                  </div>
                  <div className="ml-2 flex shrink-0 gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      className="rounded p-1 text-zinc-400 hover:bg-blue-50 hover:text-blue-500"
                      onClick={(e) => { e.stopPropagation(); openEditModal(kb); }}
                      title="编辑"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                      </svg>
                    </button>
                    <button
                      className="rounded p-1 text-zinc-400 hover:bg-red-50 hover:text-red-500"
                      onClick={(e) => { e.stopPropagation(); handleDelete(kb.id, kb.name); }}
                      title="删除"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-xs text-zinc-400">
                  <span>{kb.document_count} 篇文档</span>
                  <span>{kb.created_at ? new Date(kb.created_at).toLocaleDateString("zh-CN") : "-"}</span>
                </div>
              </div>
              );
            })}
          </div>
        )}

        {/* Document list */}
        <DocumentList
          refreshKey={docRefreshKey}
          kbFilter={kbFilter}
          onKbFilterChange={setKbFilter}
        />
      </div>

      {/* Edit KB modal */}
      {editKb && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={closeEditModal}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-1 text-sm font-semibold">编辑知识库</h3>
            <p className="mb-4 text-xs text-zinc-500">修改知识库的名称和描述</p>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">名称</label>
                <input
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  autoFocus
                  onKeyDown={(e) => { if (e.key === "Enter") handleEditSave(); }}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">描述</label>
                <textarea
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  rows={3}
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="描述（可选）"
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
                onClick={closeEditModal}
              >
                取消
              </button>
              <button
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={handleEditSave}
                disabled={!editName.trim()}
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
