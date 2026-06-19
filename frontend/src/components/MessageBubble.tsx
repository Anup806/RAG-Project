import { Loader2 } from "lucide-react";
import type { ChatMessage } from "../types";
import { CitationList } from "./CitationList";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  return (
    <article className={`message ${isAssistant ? "assistant" : "user"}`}>
      <div className="message-author">{isAssistant ? "Assistant" : "You"}</div>
      <div className="message-content">
        {message.content || (message.pending ? <Loader2 className="spin" size={18} /> : null)}
      </div>
      {isAssistant && <CitationList citations={message.citations ?? []} />}
    </article>
  );
}

