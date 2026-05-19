"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  listDocuments,
  updateDocument,
  deleteDocument,
  resyncDocument,
  listKnowledgeBases,
  uploadFile as uploadFileApi,
  ingestFile,
  createDocument,
  type Document,
  type KnowledgeBase,
  type UploadResult,
  type IngestResult,
} from "@/lib/api";
import Link from "next/link";

export default function DocumentList({
  refreshKey,
  kbFilter,
  onKbFilterChange,
}: {
  refreshKey: number;
  kbFilter: string;
  onKbFilterChange: (v: string) => void;
}) {
  const router = useRouter();

  // ── Filters ─────────────────────────────────────────────────
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);

  // ── Data ────────────────────────────────────────────────────
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Edit modal ──────────────────────────────────────────────
  const [editDoc, setEditDoc] = useState<Document | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editKbId, setEditKbId] = useState("");
  const [editMetadata, setEditMetadata] = useState<{ key: string; value: string }[]>([]);
  const [editSaving, setEditSaving] = useState(false);

  // ── Sync / delete loading ───────────────────────────────────
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // ── Upload modal ────────────────────────────────────────────
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadStep, setUploadStep] = useState<"form" | "done">("form");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadKbId, setUploadKbId] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDigest, setUploadDigest] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  // ── New document modal ──────────────────────────────────────
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [newDocFilename, setNewDocFilename] = useState("");
  const [newDocDescription, setNewDocDescription] = useState("");
  const [newDocCreating, setNewDocCreating] = useState(false);

  const resetNewDocModal = () => {
    setNewDocFilename("");
    setNewDocDescription("");
    setNewDocCreating(false);
  };

  const resetUploadModal = () => {
    setUploadStep("form");
    setUploading(false);
    setUploadResult(null);
    setIngestResult(null);
    setUploadError(null);
    setUploadKbId("");
    setUploadTitle("");
    setUploadDigest("");
    setDragOver(false);
  };

  const acceptUploadFile = useCallback(async (f: File) => {
    setUploadError(null);
    setUploading(true);
    try {
      const [uploadRes, kbList] = await Promise.all([
        uploadFileApi(f),
        listKnowledgeBases(),
      ]);
      setUploadResult(uploadRes);
      setKbs(kbList);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }, []);

  const handleIngest = async () => {
    if (!uploadResult) return;
    setUploading(true);
    setUploadError(null);
    try {
      const res = await ingestFile(
        uploadResult.file_id,
        uploadResult.filename,
        uploadTitle,
        uploadDigest,
        uploadKbId || undefined,
      );
      setIngestResult(res);
      setUploadStep("done");
      await fetchDocs();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "入库失败");
    } finally {
      setUploading(false);
    }
  };

  const handleCreateDocument = async () => {
    const raw = newDocFilename.trim();
    if (!raw) return;
    const name = raw.endsWith(".md") ? raw : `${raw}.md`;
    setNewDocCreating(true);
    try {
      const doc = await createDocument({
        filename: name,
        description: newDocDescription.trim() || undefined,
      });
      setShowNewDocModal(false);
      resetNewDocModal();
      router.push(`/editor/${doc.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建文档失败");
      setNewDocCreating(false);
    }
  };

  // ── Metadata modal ──────────────────────────────────────────
  const [metadataDoc, setMetadataDoc] = useState<Document | null>(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDocuments({
        search: search || undefined,
        knowledge_id: kbFilter || undefined,
        status: statusFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setDocs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载文档失败");
    } finally {
      setLoading(false);
    }
  }, [search, kbFilter, statusFilter, dateFrom, dateTo]);

  useEffect(() => {
    listKnowledgeBases()
      .then((data) => setKbs(data))
      .catch(() => {});
  }, []);
  useEffect(() => {
    let cancelled = false;
    listDocuments({
      search: search || undefined,
      knowledge_id: kbFilter || undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((data) => {
        if (cancelled) return;
        setDocs(data);
        setError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载文档失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [search, kbFilter, statusFilter, dateFrom, dateTo, refreshKey]);

  const resetFilters = () => {
    setSearch("");
    onKbFilterChange("");
    setStatusFilter("");
    setDateFrom("");
    setDateTo("");
  };

  // ── Edit modal ───────────────────────────────────────────────
  const openEditModal = (doc: Document) => {
    setEditDoc(doc);
    setEditName(doc.file_name);
    setEditDescription(doc.description);
    setEditKbId(doc.knowledge_id);
    // Load existing metadata into edit modal
    setEditMetadata(doc.metadata || []);
  };

  const closeEditModal = () => {
    setEditDoc(null);
    setEditSaving(false);
  };

  const handleEditSave = async () => {
    if (!editDoc) return;
    setEditSaving(true);
    try {
      const extra = editMetadata.filter(p => p.key.trim() && p.value.trim());
      await updateDocument(editDoc.id, {
        description: editDescription,
        knowledge_id: editKbId,
        metadata: extra,
      });
      closeEditModal();
      await fetchDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    } finally {
      setEditSaving(false);
    }
  };

  const addMetadataPair = () => {
    setEditMetadata([...editMetadata, { key: "", value: "" }]);
  };

  const removeMetadataPair = (index: number) => {
    setEditMetadata(editMetadata.filter((_, i) => i !== index));
  };

  const updateMetadataPair = (index: number, field: "key" | "value", val: string) => {
    const next = [...editMetadata];
    next[index] = { ...next[index], [field]: val };
    setEditMetadata(next);
  };

  // ── Actions ─────────────────────────────────────────────────
  const handleResync = async (doc: Document) => {
    setActionLoading(doc.id);
    setError(null);
    try {
      await resyncDocument(doc.id);
      await fetchDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步失败");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (doc: Document) => {
    if (!confirm(`确定删除文档「${doc.file_name}」吗？\n此操作将删除文件、向量数据，不可恢复。`)) return;
    setActionLoading(doc.id);
    setError(null);
    try {
      await deleteDocument(doc.id);
      await fetchDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setActionLoading(null);
    }
  };

  const statusLabel: Record<string, string> = {
    uploaded: "已上传",
    ingested: "已入库",
    error: "错误",
  };

  const statusColor: Record<string, string> = {
    uploaded: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
    ingested: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    error: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  };

  const isMarkdown = (name: string) => name.endsWith(".md") || name.endsWith(".markdown");

  const fileTypeConfig: Record<string, { label: string; color: string }> = {
    md: { label: "Markdown", color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
    markdown: { label: "Markdown", color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
    pdf: { label: "PDF", color: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" },
    docx: { label: "Word", color: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300" },
    doc: { label: "Word", color: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300" },
    txt: { label: "Text", color: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300" },
    html: { label: "HTML", color: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300" },
    htm: { label: "HTML", color: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300" },
  };

  function getFileTypeBadge(filename: string): { label: string; color: string } {
    const ext = filename.split(".").pop()?.toLowerCase() ?? "";
    return fileTypeConfig[ext] ?? { label: "其他", color: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400" };
  }

  return (
    <div className="border-t border-zinc-200 dark:border-zinc-800">
      {/* Section header */}
      <div className="flex items-center justify-between pt-6 pb-3">
        <div>
          <h3 className="text-sm font-semibold">文档列表</h3>
          <p className="text-xs text-zinc-500">管理所有已上传的文档，支持筛选、编辑和同步</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
            onClick={() => setShowUploadModal(true)}
          >
            上传文档
          </button>
          <button
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            onClick={() => { setShowNewDocModal(true); }}
          >
            新建文档
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 pb-4">
        <div className="min-w-[160px] flex-1">
          <label className="mb-1 block text-xs text-zinc-500">搜索文件名</label>
          <input
            className="w-full rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
            placeholder="输入关键词..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs text-zinc-500">知识库</label>
          <select
            className="w-full rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
            value={kbFilter}
            onChange={(e) => onKbFilterChange(e.target.value)}
          >
            <option value="">全部</option>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>{kb.name}</option>
            ))}
          </select>
        </div>
        <div className="w-32">
          <label className="mb-1 block text-xs text-zinc-500">状态</label>
          <select
            className="w-full rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">全部</option>
            <option value="uploaded">已上传</option>
            <option value="ingested">已入库</option>
            <option value="error">错误</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-500">从</label>
          <input
            type="date"
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-500">到</label>
          <input
            type="date"
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        <button
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
          onClick={resetFilters}
        >
          重置
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>关闭</button>
        </div>
      )}

      {/* Upload modal */}
      {showUploadModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => { if (!uploading) { setShowUploadModal(false); resetUploadModal(); } }}
        >
          <div
            className="w-full max-w-xl rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            {uploadStep === "done" && ingestResult ? (
              <>
                <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center dark:border-green-800 dark:bg-green-950">
                  <svg className="mx-auto h-10 w-10 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="mt-2 text-lg font-semibold text-green-700 dark:text-green-300">添加成功</p>
                  <p className="mt-1 text-sm text-green-600 dark:text-green-400">{ingestResult.chunks_inserted} 个文本块已存入知识库</p>
                </div>
                <button
                  className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  onClick={() => { setShowUploadModal(false); resetUploadModal(); }}
                >
                  完成
                </button>
              </>
            ) : (
              <>
                <h3 className="mb-1 text-sm font-semibold">上传文档</h3>
                <p className="mb-4 text-xs text-zinc-500">上传文档并添加到知识库</p>

                {uploadError && (
                  <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
                    {uploadError}
                  </div>
                )}

                {/* File drop zone */}
                <div
                  className={`flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                    uploadResult
                      ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950"
                      : dragOver
                        ? "border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-950"
                        : "border-zinc-300 hover:border-zinc-400 dark:border-zinc-600 dark:hover:border-zinc-500"
                  }`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    const f = e.dataTransfer.files?.[0];
                    if (f && !uploading) acceptUploadFile(f);
                  }}
                  onClick={() => { if (!uploading && !uploadResult) inputRef.current?.click(); }}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    accept=".txt,.md,.pdf,.docx,.html,.htm"
                    disabled={uploading}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) acceptUploadFile(f);
                    }}
                  />

                  {uploading && !uploadResult ? (
                    <>
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-500" />
                      <p className="text-sm text-zinc-500">上传中...</p>
                    </>
                  ) : uploadResult ? (
                    <>
                      <svg className="h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-sm font-medium text-green-700 dark:text-green-300">{uploadResult.filename}</p>
                      <p className="text-xs text-zinc-400">点击重新选择</p>
                    </>
                  ) : (
                    <>
                      <svg className="h-8 w-8 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                      <p className="text-sm text-zinc-500">拖拽文件到此处，或点击选择</p>
                      <p className="text-xs text-zinc-400">支持 TXT / MD / PDF / DOCX / HTML</p>
                    </>
                  )}
                </div>

                {/* Form fields (visible after upload) */}
                {uploadResult && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <label className="mb-1 block text-sm font-medium">标题</label>
                      <input
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                        value={uploadTitle}
                        onChange={(e) => setUploadTitle(e.target.value)}
                        placeholder="文档标题"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium">描述</label>
                      <textarea
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                        rows={2}
                        value={uploadDigest}
                        onChange={(e) => setUploadDigest(e.target.value)}
                        placeholder="文档描述（可选）"
                      />
                    </div>
                    {kbs.length > 0 && (
                      <div>
                        <label className="mb-1 block text-sm font-medium">所属知识库</label>
                        <select
                          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                          value={uploadKbId}
                          onChange={(e) => setUploadKbId(e.target.value)}
                        >
                          <option value="">不分组</option>
                          {kbs.map((kb) => (
                            <option key={kb.id} value={kb.id}>{kb.name} ({kb.document_count} 篇)</option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className="flex gap-3">
                      <button
                        className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
                        onClick={() => { setShowUploadModal(false); resetUploadModal(); }}
                        disabled={uploading}
                      >
                        取消
                      </button>
                      <button
                        className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        onClick={handleIngest}
                        disabled={uploading}
                      >
                        {uploading ? "入库中..." : "确定"}
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* New document modal */}
      {showNewDocModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => { if (!newDocCreating) { setShowNewDocModal(false); resetNewDocModal(); } }}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-1 text-sm font-semibold">新建文档</h3>
            <p className="mb-4 text-xs text-zinc-500">创建新的 Markdown 文档</p>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">文件名</label>
                <input
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  value={newDocFilename}
                  onChange={(e) => setNewDocFilename(e.target.value)}
                  placeholder="请输入文件名"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">描述</label>
                <textarea
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  rows={3}
                  value={newDocDescription}
                  onChange={(e) => setNewDocDescription(e.target.value)}
                  placeholder="可选描述"
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800 disabled:opacity-50"
                onClick={() => { setShowNewDocModal(false); resetNewDocModal(); }}
                disabled={newDocCreating}
              >
                取消
              </button>
              <button
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={handleCreateDocument}
                disabled={newDocCreating || !newDocFilename.trim()}
              >
                {newDocCreating ? "创建中..." : "创建并编辑"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="pb-6">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-500" />
          </div>
        ) : docs.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-zinc-400">暂无文档</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-700">
            <table className="w-full table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[15%]" />
                <col className="w-[10%]" />
                <col className="w-[10%]" />
                <col className="w-[10%]" />
                <col className="w-[10%]" />
                <col className="w-[25%]" />
                <col className="w-[20%]" />
              </colgroup>
              <thead className="bg-zinc-50 text-xs uppercase text-zinc-500 dark:bg-zinc-800/50">
                <tr>
                  <th className="px-4 py-3 font-medium">文件名</th>
                  <th className="px-4 py-3 font-medium">知识库</th>
                  <th className="px-4 py-3 font-medium">创建时间</th>
                  <th className="px-4 py-3 font-medium">类型</th>
                  <th className="px-4 py-3 font-medium">状态</th>
                  <th className="px-4 py-3 font-medium">元数据</th>
                  <th className="px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30">
                    {/* Filename */}
                    <td className="px-4 py-3">
                      {!isMarkdown(doc.file_name) && (<span className="block truncate font-medium" title={doc.file_name}>
                        {doc.file_name}
                      </span>)}
                       {isMarkdown(doc.file_name) && (
                          <Link
                            className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-100 dark:bg-blue-950 dark:text-blue-400 dark:hover:bg-blue-900"
                            href={`/editor/${doc.id}`}
                          >
                            {doc.file_name}
                          </Link>
                        )}
                    </td>

                    {/* Knowledge base */}
                    <td className="px-4 py-3">
                      <span className="block truncate text-zinc-500" title={
                        doc.knowledge_id
                          ? kbs.find((kb) => kb.id === doc.knowledge_id)?.name || doc.knowledge_id
                          : "-"
                      }>
                        {doc.knowledge_id
                          ? kbs.find((kb) => kb.id === doc.knowledge_id)?.name || doc.knowledge_id
                          : "-"}
                      </span>
                    </td>

                    {/* Created at */}
                    <td className="px-4 py-3 text-zinc-500">
                      {doc.created_at
                        ? new Date(doc.created_at).toLocaleDateString("zh-CN")
                        : "-"}
                    </td>

                    {/* Type badge */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          getFileTypeBadge(doc.file_name).color
                        }`}
                      >
                        {getFileTypeBadge(doc.file_name).label}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          statusColor[doc.status] || "bg-zinc-100 text-zinc-600"
                        }`}
                      >
                        {statusLabel[doc.status] || doc.status}
                      </span>
                    </td>

                    {/* Metadata */}
                    <td className="px-4 py-3 text-xs leading-relaxed text-zinc-500">
                      <div className="truncate font-medium text-zinc-700 dark:text-zinc-300">
                        <span className="text-zinc-400">名称：</span>{doc.file_name}
                      </div>
                      {doc.description && (
                        <div className="truncate" title={doc.description}>
                          <span className="text-zinc-400">描述：</span>{doc.description}
                        </div>
                      )}
                      {doc.knowledge_id && (
                        <div>
                          <span className="text-zinc-400">知识库：</span>
                          <span className="text-blue-600 dark:text-blue-400">
                            {kbs.find((kb) => kb.id === doc.knowledge_id)?.name || doc.knowledge_id}
                          </span>
                        </div>
                      )}
                      {doc.created_at && (
                        <div>
                          <span className="text-zinc-400">时间：</span>
                          {new Date(doc.created_at).toLocaleDateString("zh-CN")}
                        </div>
                      )}
                      {doc.metadata && doc.metadata.length > 0 && (
                        <div className="border-t border-zinc-100 pt-1 mt-1 dark:border-zinc-700">
                          {doc.metadata.map((item, i) => (
                            <div key={i} className="truncate">
                              <span className="text-zinc-400">{item.key}：</span>{item.value}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          className="rounded bg-zinc-100 px-2 py-1 text-xs font-medium hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700"
                          onClick={() => openEditModal(doc)}
                        >
                          编辑
                        </button>
                        <button
                          className="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-600 hover:bg-green-100 disabled:opacity-50 dark:bg-green-950 dark:text-green-400 dark:hover:bg-green-900"
                          onClick={() => handleResync(doc)}
                          disabled={actionLoading === doc.id}
                          title="重新同步到向量数据库"
                        >
                          {actionLoading === doc.id ? "..." : "同步"}
                        </button>
                        <button
                          className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-50 dark:bg-red-950 dark:text-red-400 dark:hover:bg-red-900"
                          onClick={() => handleDelete(doc)}
                          disabled={actionLoading === doc.id}
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Metadata modal */}
      {metadataDoc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setMetadataDoc(null)}
        >
          <div
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-4 text-sm font-semibold">文档元数据</h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-zinc-500">文件 ID</dt>
                <dd className="font-mono text-xs">{metadataDoc.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-zinc-500">文件路径</dt>
                <dd className="max-w-[200px] truncate font-mono text-xs" title={metadataDoc.file_path}>{metadataDoc.file_path || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-zinc-500">创建时间</dt>
                <dd>{metadataDoc.created_at ? new Date(metadataDoc.created_at).toLocaleString("zh-CN") : "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-zinc-500">描述</dt>
                <dd className="max-w-[200px] truncate" title={metadataDoc.description}>{metadataDoc.description || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-zinc-500">知识库 ID</dt>
                <dd className="font-mono text-xs">{metadataDoc.knowledge_id || "-"}</dd>
              </div>
            </dl>
            <div className="mt-6 flex justify-end">
              <button
                className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
                onClick={() => setMetadataDoc(null)}
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editDoc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => { if (!editSaving) closeEditModal(); }}
        >
          <div
            className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-1 text-sm font-semibold">编辑元数据</h3>
            <p className="mb-4 text-xs text-zinc-500">修改文档的元数据信息</p>

            <div className="space-y-4">
              {/* File name */}
              <div>
                <label className="mb-1 block text-sm font-medium">名称</label>
                <input
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-sm font-medium">描述</label>
                <textarea
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  rows={2}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
              </div>

              {/* Knowledge base */}
              <div>
                <label className="mb-1 block text-sm font-medium">所属知识库</label>
                <select
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                  value={editKbId}
                  onChange={(e) => setEditKbId(e.target.value)}
                >
                  <option value="">不分组</option>
                  {kbs.map((kb) => (
                    <option key={kb.id} value={kb.id}>{kb.name}</option>
                  ))}
                </select>
              </div>

              {/* Dynamic key-value metadata */}
              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-sm font-medium">自定义元数据</label>
                  <button
                    className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                    onClick={addMetadataPair}
                  >
                    + 添加
                  </button>
                </div>
                <div className="space-y-2">
                  {editMetadata.length === 0 && (
                    <p className="text-xs text-zinc-400">暂无自定义元数据</p>
                  )}
                  {editMetadata.map((pair, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <input
                        className="w-2/5 rounded-lg border border-zinc-300 px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                        placeholder="关键字"
                        value={pair.key}
                        onChange={(e) => updateMetadataPair(i, "key", e.target.value)}
                      />
                      <input
                        className="flex-1 rounded-lg border border-zinc-300 px-2 py-1.5 text-xs focus:border-blue-500 focus:outline-none dark:border-zinc-600 dark:bg-zinc-800"
                        placeholder="value"
                        value={pair.value}
                        onChange={(e) => updateMetadataPair(i, "value", e.target.value)}
                      />
                      <button
                        className="text-zinc-400 hover:text-red-500"
                        onClick={() => removeMetadataPair(i)}
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
                onClick={closeEditModal}
                disabled={editSaving}
              >
                取消
              </button>
              <button
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                onClick={handleEditSave}
                disabled={editSaving}
              >
                {editSaving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
