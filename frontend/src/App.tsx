import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Database, RefreshCw } from "lucide-react";
import {
  createSession,
  deleteDocument,
  deleteSession,
  listDocuments,
  listMessages,
  listSessions,
  streamMessage,
  updateSession,
  uploadDocuments
} from "./api/client";
import { ChatWindow } from "./components/ChatWindow";
import { DocumentList } from "./components/DocumentList";
import { SessionList } from "./components/SessionList";
import { UploadDropzone } from "./components/UploadDropzone";
import type { ChatMessage, ChatSession, Citation, DocumentRecord } from "./types";

export default function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string>();

  const processedCount = useMemo(() => documents.filter((document) => document.status === "processed").length, [documents]);
  const activeSession = sessions.find((session) => session.id === activeSessionId);

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    const hasProcessing = documents.some((document) => document.status === "pending" || document.status === "processing");
    if (!hasProcessing) return;
    const interval = window.setInterval(() => {
      void refreshDocuments();
    }, 3000);
    return () => window.clearInterval(interval);
  }, [documents]);

  async function bootstrap() {
    setLoading(true);
    setError(undefined);
    try {
      const [docs, existingSessions] = await Promise.all([listDocuments(), listSessions()]);
      setDocuments(docs);
      if (existingSessions.length) {
        setSessions(existingSessions);
        await activateSession(existingSessions[0]);
      } else {
        const session = await createSession();
        setSessions([session]);
        await activateSession(session);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the app.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshDocuments() {
    try {
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh documents.");
    }
  }

  async function refreshSessions() {
    try {
      setSessions(await listSessions());
    } catch {
      // Session refresh is cosmetic; message streaming should not be interrupted.
    }
  }

  async function activateSession(session: ChatSession) {
    setActiveSessionId(session.id);
    setSelectedDocumentIds(session.selected_document_ids);
    setActiveCitations([]);
    const history = await listMessages(session.id);
    setMessages(history);
  }

  async function handleCreateSession() {
    try {
      const session = await createSession(selectedDocumentIds);
      setSessions((current) => [session, ...current]);
      await activateSession(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat.");
    }
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await deleteSession(sessionId);
      const remaining = sessions.filter((session) => session.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining.length) {
          await activateSession(remaining[0]);
        } else {
          const session = await createSession();
          setSessions([session]);
          await activateSession(session);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete chat.");
    }
  }

  async function handleUpload(files: File[]) {
    setUploading(true);
    setError(undefined);
    try {
      const uploaded = await uploadDocuments(files);
      setDocuments((current) => [...uploaded, ...current]);
      window.setTimeout(() => void refreshDocuments(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      const nextSelected = selectedDocumentIds.filter((id) => id !== documentId);
      setSelectedDocumentIds(nextSelected);
      if (activeSessionId) {
        await updateSession(activeSessionId, nextSelected);
        await refreshSessions();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document.");
    }
  }

  async function toggleDocument(documentId: string) {
    if (!activeSessionId) return;
    const next = selectedDocumentIds.includes(documentId)
      ? selectedDocumentIds.filter((id) => id !== documentId)
      : [...selectedDocumentIds, documentId];
    setSelectedDocumentIds(next);
    try {
      const updated = await updateSession(activeSessionId, next);
      setSessions((current) => current.map((session) => (session.id === updated.id ? updated : session)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update document filters.");
    }
  }

  async function ask(question: string) {
    if (!activeSessionId || streaming) return;
    setStreaming(true);
    setError(undefined);
    setActiveCitations([]);

    const userMessage: ChatMessage = {
      id: `local-user-${Date.now()}`,
      session_id: activeSessionId,
      role: "user",
      content: question,
      citations: [],
      created_at: new Date().toISOString()
    };
    const pendingId = `local-assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: pendingId,
      session_id: activeSessionId,
      role: "assistant",
      content: "",
      citations: [],
      created_at: new Date().toISOString(),
      pending: true
    };
    setMessages((current) => [...current, userMessage, assistantMessage]);

    try {
      await streamMessage(activeSessionId, question, selectedDocumentIds, {
        onSources: (sources) => {
          setActiveCitations(sources);
          setMessages((current) =>
            current.map((message) => (message.id === pendingId ? { ...message, citations: sources } : message))
          );
        },
        onToken: (token) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === pendingId ? { ...message, content: `${message.content}${token}` } : message
            )
          );
        },
        onDone: (message, sources) => {
          setMessages((current) =>
            current.map((item) => (item.id === pendingId ? { ...message, citations: sources, pending: false } : item))
          );
          void refreshSessions();
        },
        onError: (detail) => {
          setError(detail);
          setMessages((current) =>
            current.map((message) =>
              message.id === pendingId ? { ...message, content: detail, pending: false } : message
            )
          );
        }
      });
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Streaming failed.";
      setError(detail);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId ? { ...message, content: detail, pending: false } : message
        )
      );
    } finally {
      setStreaming(false);
    }
  }

  const scopeLabel = selectedDocumentIds.length
    ? `${selectedDocumentIds.length} selected`
    : processedCount
      ? "All processed PDFs"
      : "No processed PDFs";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-icon">
            <Database size={19} />
          </div>
          <div>
            <strong>PDF RAG</strong>
            <span>{scopeLabel}</span>
          </div>
        </div>

        <UploadDropzone disabled={uploading} onUpload={handleUpload} />

        <section className="sidebar-section">
          <div className="section-title">
            <span>Documents</span>
            <button className="icon-button subtle" onClick={() => void refreshDocuments()} title="Refresh documents" type="button">
              <RefreshCw size={15} />
            </button>
          </div>
          <DocumentList
            documents={documents}
            onDelete={handleDeleteDocument}
            onToggle={toggleDocument}
            selectedIds={selectedDocumentIds}
          />
        </section>

        <section className="sidebar-section history-section">
          <div className="section-title">
            <span>History</span>
          </div>
          <SessionList
            activeId={activeSessionId}
            onCreate={handleCreateSession}
            onDelete={handleDeleteSession}
            onSelect={(sessionId) => {
              const session = sessions.find((item) => item.id === sessionId);
              if (session) void activateSession(session);
            }}
            sessions={sessions}
          />
        </section>
      </aside>

      <div className="workarea">
        {error && (
          <div className="error-banner">
            <AlertCircle size={17} />
            <span>{error}</span>
          </div>
        )}
        <ChatWindow
          activeCitations={activeCitations}
          disabled={loading || !activeSession || !processedCount}
          messages={messages}
          onSubmit={ask}
          streaming={streaming}
        />
      </div>
    </div>
  );
}

