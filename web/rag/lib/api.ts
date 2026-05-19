// ── Auth helpers ─────────────────────────────────────────────────

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Auth API ────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export async function login(req: LoginRequest): Promise<TokenResponse> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err === "用户名或密码错误" ? err : `登录失败 (${res.status})`);
  }
  return res.json();
}

export async function register(req: RegisterRequest): Promise<TokenResponse> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err === "用户名已存在" || err === "邮箱已被注册" ? err : `注册失败 (${res.status})`);
  }
  return res.json();
}

export async function getMe(): Promise<User> {
  const res = await fetch("/api/auth/me", {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("获取用户信息失败");
  return res.json();
}

// ── RAG (upload / ingest) ──────────────────────────────────────

export interface UploadResult {
  file_id: string;
  filename: string;
}

export interface IngestMetadata {
  title?: string;
  digest?: string;
  topic?: string;
  sub_topic?: string;
  question_category?: string;
  keywords?: string[];
  version?: string;
}

export interface IngestResult {
  message: string;
  filename: string;
  chunks_inserted: number;
  knowledge_id?: string;
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/upload", { method: "POST", body: form, headers: { ...getAuthHeaders() } });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Upload failed (${res.status}): ${err}`);
  }
  return res.json();
}

export async function ingestFile(
  fileId: string,
  filename: string,
  title: string,
  description: string,
  knowledgeId?: string,
): Promise<IngestResult> {
  const res = await fetch("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      file_id: fileId,
      filename,
      title,
      description,
      knowledge_id: knowledgeId ?? "",
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Ingest failed (${res.status}): ${err}`);
  }
  return res.json();
}

// ── Knowledge Base ─────────────────────────────────────────────

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  created_at: string;
  document_count: number;
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await fetch("/api/knowledges", { headers: { ...getAuthHeaders() } });
  if (!res.ok) throw new Error("Failed to list knowledge bases");
  return res.json();
}

export async function createKnowledgeBase(
  name: string,
  description?: string,
): Promise<KnowledgeBase> {
  const res = await fetch("/api/knowledges", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ name, description: description ?? "" }),
  });
  if (!res.ok) throw new Error("Failed to create knowledge base");
  return res.json();
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  const res = await fetch(`/api/knowledges/${id}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to delete knowledge base");
}

export async function updateKnowledgeBase(
  id: string,
  data: { name?: string; description?: string },
): Promise<KnowledgeBase> {
  const res = await fetch(`/api/knowledges/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update knowledge base");
  return res.json();
}

// ── Document ────────────────────────────────────────────────────

export interface Document {
  id: string;
  file_id: string;
  file_name: string;
  description: string;
  knowledge_id: string;
  created_at: string;
  file_path: string;
  status: string;
  metadata: { key: string; value: string }[];
}

export interface DocumentUpdate {
  description?: string;
  knowledge_id?: string;
  metadata?: { key: string; value: string }[];
}

export interface DocumentContent {
  content: string;
  file_name: string;
}

export async function listDocuments(
  params?: {
    knowledge_id?: string;
    search?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
  },
): Promise<Document[]> {
  const searchParams = new URLSearchParams();
  if (params?.knowledge_id) searchParams.set("knowledge_id", params.knowledge_id);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.date_from) searchParams.set("date_from", params.date_from);
  if (params?.date_to) searchParams.set("date_to", params.date_to);

  const qs = searchParams.toString();
  const res = await fetch(`/api/documents${qs ? `?${qs}` : ""}`, { headers: { ...getAuthHeaders() } });
  if (!res.ok) throw new Error("Failed to list documents");
  return res.json();
}

export async function updateDocument(
  docId: string,
  updates: DocumentUpdate,
): Promise<Document> {
  const res = await fetch(`/api/documents/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update document");
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`/api/documents/${docId}`, { method: "DELETE", headers: { ...getAuthHeaders() } });
  if (!res.ok) throw new Error("Failed to delete document");
}

export async function getDocumentContent(docId: string): Promise<DocumentContent> {
  const res = await fetch(`/api/documents/${docId}/content`, { headers: { ...getAuthHeaders() } });
  if (!res.ok) throw new Error("Failed to get document content");
  return res.json();
}

export async function updateDocumentContent(
  docId: string,
  content: string,
): Promise<{ message: string; chunks_inserted: number }> {
  const res = await fetch(`/api/documents/${docId}/content`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error("Failed to update document content");
  return res.json();
}

export async function resyncDocument(
  docId: string,
): Promise<{ message: string; chunks_inserted: number }> {
  const res = await fetch(`/api/documents/${docId}/resync`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to resync document");
  return res.json();
}

export interface CreateDocumentRequest {
  filename: string;
  description?: string;
  knowledge_id?: string;
}

export async function createDocument(
  req: CreateDocumentRequest,
): Promise<Document> {
  const res = await fetch("/api/documents/create", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Create document failed (${res.status}): ${err}`);
  }
  return res.json();
}

// ── Chat History ────────────────────────────────────────────────

export interface HistoryMessage {
  id: string;
  query: string;
  response: string;
  created_at: string;
  rating: number | null;
  comment: string | null;
  error: string | null;
}

export interface ChatHistoryResponse {
  messages: HistoryMessage[];
  has_more: boolean;
}

export async function getChatHistory(
  beforeId?: string,
  limit = 20,
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (beforeId) params.set("before_id", beforeId);
  const res = await fetch(`/api/chat/history?${params.toString()}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch chat history");
  return res.json();
}

// ── Chat ───────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function chatSend(
  query: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ query }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Chat failed (${res.status}): ${err}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Response body is not readable");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.content) {
            onChunk(parsed.content);
          }
        } catch {
          onChunk(data);
        }
      }
    }
  }
}
