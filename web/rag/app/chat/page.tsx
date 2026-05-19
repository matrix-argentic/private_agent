"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { mdComponents } from "@/app/editor/_components/mdComponents";
import { chatSend, getChatHistory, type HistoryMessage } from "@/lib/api";

interface DisplayMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const PAGE_SIZE = 20;

export default function ChatPage() {
  const [messages, setMessages] = useState<DisplayMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const cursorRef = useRef<string | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const topSentinelRef = useRef<HTMLDivElement>(null);
  const loadingMoreRef = useRef(false);
  const initialScrolled = useRef(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  // ── Load initial history ──────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    getChatHistory(undefined, PAGE_SIZE)
      .then((res) => {
        if (cancelled) return;
        const msgs = historyToMessages(res.messages);
        setMessages(msgs);
        setHasMore(res.has_more);
        cursorRef.current = res.messages.length > 0 ? res.messages[res.messages.length - 1].id : undefined;
      })
      .catch((e) => setHistoryError(e instanceof Error ? e.message : "加载历史记录失败"))
      .finally(() => {
        if (!cancelled) {
          setHistoryLoading(false);
          // Scroll to bottom after DOM paints with loaded messages
          requestAnimationFrame(() => {
            const scroll = () => bottomRef.current?.scrollIntoView({ behavior: "auto" });
            scroll();
            initialScrolled.current = true;
            // Re-scroll after images finish loading (they load async and shift layout)
            setTimeout(scroll, 600);
            setTimeout(scroll, 2000);
          });
        }
      });
    return () => { cancelled = true; };
  }, []);

  // ── Scroll to bottom when new messages arrive ────────────
  useEffect(() => {
    if (!initialScrolled.current) return;
    if (loadingMoreRef.current) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // ── IntersectionObserver for pre-loading history ───────────
  useEffect(() => {
    const sentinel = topSentinelRef.current;
    if (!sentinel || !hasMore || historyLoading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && hasMore && !loadingMoreRef.current) {
            loadMore();
          }
        }
      },
      { rootMargin: "400px 0px 0px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMore, historyLoading, messages.length]);

  const loadMore = useCallback(async () => {
    if (loadingMoreRef.current || !cursorRef.current) return;
    loadingMoreRef.current = true;

    const container = scrollRef.current;
    const prevScrollHeight = container?.scrollHeight ?? 0;
    const prevScrollTop = container?.scrollTop ?? 0;

    try {
      const res = await getChatHistory(cursorRef.current, PAGE_SIZE);
      if (res.messages.length === 0) {
        setHasMore(false);
        return;
      }
      const older = historyToMessages(res.messages);
      setMessages((prev) => [...older, ...prev]);
      setHasMore(res.has_more);
      cursorRef.current = res.messages[res.messages.length - 1].id;

      // maintain scroll position after prepending
      requestAnimationFrame(() => {
        if (container) {
          container.scrollTop = container.scrollHeight - prevScrollHeight + prevScrollTop;
        }
      });
    } catch {
      // ignore silently
    } finally {
      loadingMoreRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Track scroll position to show "back to bottom" button ──
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 150;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setShowScrollBtn(!isNearBottom);
  }, []);

  // ── Send message ──────────────────────────────────────────
  const send = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setError(null);

    const userMsg: DisplayMsg = { id: `user_${Date.now()}`, role: "user", content: query };
    const tempAssistant: DisplayMsg = { id: `assistant_${Date.now()}`, role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMsg, tempAssistant]);
    setLoading(true);

    try {
      let fullContent = "";
      await chatSend(query, (chunk) => {
        fullContent += chunk;
        setMessages((prev) => {
          const next = [...prev];
          const last = { ...next[next.length - 1], content: fullContent };
          next[next.length - 1] = last;
          return next;
        });
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "请求失败";
      setError(msg);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <h2 className="text-sm font-semibold">对话</h2>
        <p className="text-xs text-zinc-500">与知识库 AI 助手对话</p>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0" onScroll={handleScroll}>
        {/* Top sentinel for scroll-up pagination */}
        {hasMore && <div ref={topSentinelRef} className="h-4" />}

        {historyLoading && (
          <div className="flex items-center justify-center py-10">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-500" />
          </div>
        )}

        {historyError && (
          <div className="mx-auto max-w-3xl px-4 pt-4">
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-2 text-sm text-yellow-700 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-400">
              {historyError}
            </div>
          </div>
        )}

        {!historyLoading && messages.length === 0 && !loading && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <svg className="mx-auto h-10 w-10 text-zinc-300 dark:text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
              <p className="mt-3 text-sm text-zinc-400">发送一条消息开始对话</p>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "whitespace-pre-wrap bg-blue-600 text-white"
                    : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                }`}
              >
                {msg.role === "user" ? (
                  msg.content
                ) : (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={mdComponents}
                  >
                    {msg.content || "..."}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1.5 rounded-2xl bg-zinc-100 px-4 py-3 dark:bg-zinc-800">
                <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" style={{ animationDelay: "0ms" }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" style={{ animationDelay: "150ms" }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />

        {/* Scroll-to-bottom button — sticky at bottom-right when scrolled up */}
        {showScrollBtn && (
          <div className="sticky bottom-6 flex justify-end pr-6 pointer-events-none">
            <button
              onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
              className="pointer-events-auto flex h-10 w-10 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-600 shadow-lg transition hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
              aria-label="滚动到最新消息"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-auto max-w-3xl px-4 pb-2">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
            {error}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-zinc-200 p-4 dark:border-zinc-800">
        <div className="mx-auto flex max-w-3xl gap-3">
          <input
            className="flex-1 rounded-xl border border-zinc-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none disabled:opacity-50 dark:border-zinc-600 dark:bg-zinc-800"
            placeholder="输入消息..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={loading}
          />
          <button
            className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            onClick={send}
            disabled={loading || !input.trim()}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────

function historyToMessages(records: HistoryMessage[]): DisplayMsg[] {
  const result: DisplayMsg[] = [];
  // API returns newest first; reverse to get chronological order
  for (let i = records.length - 1; i >= 0; i--) {
    const r = records[i];
    result.push({ id: `q_${r.id}`, role: "user", content: r.query });
    result.push({ id: `a_${r.id}`, role: "assistant", content: r.response });
  }
  return result;
}
