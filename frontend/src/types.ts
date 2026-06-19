export type DocumentStatus = "pending" | "processing" | "processed" | "failed";

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: DocumentStatus;
  page_count: number;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  selected_document_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Citation {
  filename: string;
  document_id: string;
  page_number: number;
  chunk_id: string;
  text: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
  pending?: boolean;
}

export interface StreamCallbacks {
  onSources?: (sources: Citation[]) => void;
  onToken?: (token: string) => void;
  onDone?: (message: ChatMessage, sources: Citation[]) => void;
  onError?: (message: string) => void;
}

