"use client";

import { useState, useRef } from "react";
import type { Components } from "react-markdown";

export const mdComponents: Components = {
  /* ── Headings ────────────────────────────────────────────── */
  h1: ({ node, children, ...rest }) => (
    <h1 className="mb-4 mt-8 text-3xl font-bold tracking-tight first:mt-0" {...rest}>
      {children}
    </h1>
  ),
  h2: ({ node, children, ...rest }) => (
    <h2 className="mb-3 mt-6 text-2xl font-semibold tracking-tight" {...rest}>
      {children}
    </h2>
  ),
  h3: ({ node, children, ...rest }) => (
    <h3 className="mb-2 mt-5 text-xl font-semibold" {...rest}>{children}</h3>
  ),
  h4: ({ node, children, ...rest }) => (
    <h4 className="mb-2 mt-4 text-lg font-medium" {...rest}>{children}</h4>
  ),

  /* ── Paragraph ───────────────────────────────────────────── */
  p: ({ node, children, ...rest }) => (
    <p className="mb-4 leading-7" {...rest}>{children}</p>
  ),

  /* ── Lists ───────────────────────────────────────────────── */
  ul: ({ node, children, ...rest }) => (
    <ul className="mb-4 list-disc space-y-1 pl-6" {...rest}>{children}</ul>
  ),
  ol: ({ node, children, ...rest }) => (
    <ol className="mb-4 list-decimal space-y-1 pl-6" {...rest}>{children}</ol>
  ),
  li: ({ node, children, ...rest }) => (
    <li className="leading-7" {...rest}>{children}</li>
  ),

  /* ── Inline & Block Code ─────────────────────────────────── */
  code: ({ node, children, className, ...rest }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded-md bg-zinc-100 px-1.5 py-0.5 font-mono text-sm text-pink-600 dark:bg-zinc-800 dark:text-pink-400"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...rest }) => {
    const preRef = useRef<HTMLPreElement>(null);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
      const code = preRef.current?.querySelector("code")?.textContent || "";
      try {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // clipboard not available
      }
    };

    return (
      <div className="group relative mb-5">
        <button
          onClick={handleCopy}
          className="absolute right-2 top-2 z-10 rounded-md px-2 py-1 text-xs text-zinc-400 opacity-0 transition-opacity hover:bg-zinc-700 hover:text-zinc-200 group-hover:opacity-100"
        >
          {copied ? "已复制" : "复制"}
        </button>
        <pre
          ref={preRef}
          className="overflow-x-auto rounded-xl bg-zinc-900 p-4 text-[13px] leading-relaxed text-zinc-100 ring-1 ring-zinc-700/50 dark:bg-black"
          {...rest}
        >
          {children}
        </pre>
      </div>
    );
  },

  /* ── Blockquote ──────────────────────────────────────────── */
  blockquote: ({ node, children, ...rest }) => (
    <blockquote
      className="mb-4 rounded-r-xl border-l-4 border-blue-500 bg-zinc-50 py-3 pl-4 pr-4 text-zinc-600 dark:bg-zinc-800/40 dark:text-zinc-400"
      {...rest}
    >
      {children}
    </blockquote>
  ),

  /* ── Links ───────────────────────────────────────────────── */
  a: ({ node, children, href, ...rest }) => (
    <a
      className="font-medium text-blue-600 underline decoration-blue-300 decoration-1 underline-offset-2 hover:text-blue-800 hover:decoration-blue-500 dark:text-blue-400 dark:decoration-blue-600 dark:hover:text-blue-300"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      {...rest}
    >
      {children}
    </a>
  ),

  /* ── Tables ──────────────────────────────────────────────── */
  table: ({ node, children, ...rest }) => (
    <div className="mb-5 overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-700">
      <table className="w-full border-collapse text-sm" {...rest}>{children}</table>
    </div>
  ),
  th: ({ node, children, ...rest }) => (
    <th
      className="border-b border-zinc-200 bg-zinc-50 px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:border-zinc-700 dark:bg-zinc-800/50 dark:text-zinc-400"
      {...rest}
    >
      {children}
    </th>
  ),
  td: ({ node, children, ...rest }) => (
    <td
      className="border-b border-zinc-100 px-4 py-2.5 dark:border-zinc-800"
      {...rest}
    >
      {children}
    </td>
  ),

  /* ── Checkbox (task lists) ───────────────────────────────── */
  input: (props) => (
    <input className="mr-1.5 -mt-0.5 inline-block align-middle accent-blue-500" {...props} />
  ),

  /* ── Image ───────────────────────────────────────────────── */
  img: ({ src, alt }) => {
    if (!src) return null;
    return (
      <img
        className="my-4 max-w-full rounded-xl border border-zinc-200 dark:border-zinc-700"
        src={src}
        alt={alt || ""}
      />
    );
  },

  /* ── Horizontal Rule ─────────────────────────────────────── */
  hr: ({ node, ...rest }) => (
    <hr className="my-8 border-zinc-200 dark:border-zinc-700" {...rest} />
  ),
};
