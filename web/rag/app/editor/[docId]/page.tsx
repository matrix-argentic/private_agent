"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import {
  getDocumentContent,
  updateDocumentContent,
  type DocumentContent,
} from "@/lib/api";
import { mdComponents } from "@/app/editor/_components/mdComponents";

export default function EditorPage() {
  const { docId } = useParams<{ docId: string }>();
  const router = useRouter();

  const [doc, setDoc] = useState<DocumentContent | null>(null);
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isDirty = content !== originalContent;

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    getDocumentContent(docId)
      .then((data) => {
        if (cancelled) return;
        setDoc(data);
        setContent(data.content);
        setOriginalContent(data.content);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [docId]);

  const handleSave = async () => {
    if (!docId || !isDirty) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await updateDocumentContent(docId, content);
      setOriginalContent(content);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <button
            className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800"
            onClick={() => router.back()}
            title="返回"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
          </button>
          <div>
            <h2 className="text-sm font-semibold">
              {doc?.file_name || "编辑器"}
            </h2>
            <p className="text-xs text-zinc-500">
              {isDirty ? "有未保存的更改" : "已保存"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
            onClick={() => setShowPreview((v) => !v)}
          >
            {showPreview ? "仅编辑" : "预览"}
          </button>
          {saved && (
            <span className="text-xs text-green-600">保存成功</span>
          )}
          <button
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            onClick={handleSave}
            disabled={saving || !isDirty}
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>关闭</button>
        </div>
      )}

      {/* Editor + Preview */}
      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-500" />
        </div>
      ) : (
        <div className="flex flex-1 divide-x divide-zinc-200 dark:divide-zinc-800">
          {/* Edit pane */}
          <div className="flex flex-1 flex-col">
            <div className="border-b border-zinc-100 px-6 py-2 text-xs text-zinc-400 dark:border-zinc-800">
              编辑
            </div>
            <textarea
              ref={textareaRef}
              className="h-full w-full resize-none border-0 bg-transparent px-6 py-4 font-mono text-sm leading-relaxed focus:outline-none"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>

          {/* Preview pane */}
          {showPreview && (
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="border-b border-zinc-100 px-6 py-2 text-xs text-zinc-400 dark:border-zinc-800">
                预览
              </div>
              <div className="flex-1 overflow-y-auto px-6 py-4">
                <div className="prose prose-zinc max-w-none dark:prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={mdComponents}>
                    {content || "*暂无内容*"}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
