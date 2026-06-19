import { MessageSquare, Plus, Trash2 } from "lucide-react";
import type { ChatSession } from "../types";

interface SessionListProps {
  sessions: ChatSession[];
  activeId?: string;
  onCreate: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

export function SessionList({ sessions, activeId, onCreate, onSelect, onDelete }: SessionListProps) {
  return (
    <div className="sessions">
      <button className="new-chat-button" onClick={onCreate} type="button">
        <Plus size={17} />
        <span>New Chat</span>
      </button>
      <div className="session-list">
        {sessions.map((session) => (
          <div className={`session-row ${session.id === activeId ? "is-active" : ""}`} key={session.id}>
            <button className="session-main" onClick={() => onSelect(session.id)} title={session.title} type="button">
              <MessageSquare size={16} />
              <span>{session.title}</span>
            </button>
            <button className="icon-button subtle" onClick={() => onDelete(session.id)} title="Delete chat" type="button">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

