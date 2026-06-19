import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import type { ChatMessage, Citation } from "../types";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: ChatMessage[];
  streaming: boolean;
  disabled: boolean;
  activeCitations: Citation[];
  onSubmit: (question: string) => void;
}

export function ChatWindow({ messages, streaming, disabled, activeCitations, onSubmit }: ChatWindowProps) {
  const messagesRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = messagesRef.current;
    if (!element) return;
    element.scrollTop = element.scrollHeight;
  }, [messages, streaming]);

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div className="assistant-mark">
          <Bot size={20} />
        </div>
        <div>
          <h1>PDF Knowledge Assistant</h1>
          <p>{activeCitations.length ? `${activeCitations.length} source chunks selected` : "Grounded answers from uploaded PDFs"}</p>
        </div>
      </header>
      <section className="messages" ref={messagesRef}>
        {messages.length ? (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        ) : (
          <div className="empty-chat">
            <Bot size={24} />
            <span>Ask a question after your PDFs finish processing.</span>
          </div>
        )}
      </section>
      <Composer disabled={disabled} onSubmit={onSubmit} streaming={streaming} />
    </main>
  );
}

