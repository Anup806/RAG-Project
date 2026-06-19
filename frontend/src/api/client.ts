import type { ChatMessage, ChatSession, Citation, DocumentRecord, StreamCallbacks } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const detail = await safeError(response);
    throw new Error(detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function safeError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const data = await request<{ documents: DocumentRecord[] }>("/documents");
  return data.documents;
}

export async function uploadDocuments(files: File[]): Promise<DocumentRecord[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(await safeError(response));
  }
  const data = (await response.json()) as { documents: DocumentRecord[] };
  return data.documents;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await request<void>(`/documents/${documentId}`, { method: "DELETE" });
}

export async function listSessions(): Promise<ChatSession[]> {
  const data = await request<{ sessions: ChatSession[] }>("/chat/sessions");
  return data.sessions;
}

export async function createSession(documentIds: string[] = []): Promise<ChatSession> {
  return request<ChatSession>("/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ document_ids: documentIds })
  });
}

export async function updateSession(sessionId: string, documentIds: string[]): Promise<ChatSession> {
  return request<ChatSession>(`/chat/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ document_ids: documentIds })
  });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await request<void>(`/chat/sessions/${sessionId}`, { method: "DELETE" });
}

export async function listMessages(sessionId: string): Promise<ChatMessage[]> {
  const data = await request<{ messages: ChatMessage[] }>(`/chat/sessions/${sessionId}/messages`);
  return data.messages;
}

export async function streamMessage(
  sessionId: string,
  question: string,
  documentIds: string[],
  callbacks: StreamCallbacks
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      document_ids: documentIds.length ? documentIds : undefined
    })
  });

  if (!response.ok || !response.body) {
    throw new Error(await safeError(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const raw of events) {
      const event = parseSse(raw);
      if (!event) continue;
      if (event.event === "sources") {
        callbacks.onSources?.(event.data.sources as Citation[]);
      }
      if (event.event === "token") {
        callbacks.onToken?.(event.data.token as string);
      }
      if (event.event === "done") {
        callbacks.onDone?.(event.data.message as ChatMessage, event.data.sources as Citation[]);
      }
      if (event.event === "error") {
        callbacks.onError?.(event.data.detail as string);
      }
    }
  }
}

function parseSse(raw: string): { event: string; data: Record<string, unknown> } | null {
  const lines = raw.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event:"));
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!eventLine || !dataLine) return null;
  const event = eventLine.replace("event:", "").trim();
  const data = JSON.parse(dataLine.replace("data:", "").trim()) as Record<string, unknown>;
  return { event, data };
}

