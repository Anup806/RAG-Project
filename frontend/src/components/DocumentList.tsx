import { AlertTriangle, CheckCircle2, Clock3, FileText, Loader2, Trash2 } from "lucide-react";
import type { DocumentRecord } from "../types";

interface DocumentListProps {
  documents: DocumentRecord[];
  selectedIds: string[];
  onToggle: (documentId: string) => void;
  onDelete: (documentId: string) => void;
}

export function DocumentList({ documents, selectedIds, onToggle, onDelete }: DocumentListProps) {
  if (!documents.length) {
    return <div className="empty-small">No PDFs yet</div>;
  }

  return (
    <div className="document-list">
      {documents.map((document) => {
        const selected = selectedIds.includes(document.id);
        const selectable = document.status === "processed";
        return (
          <div className={`document-row ${selected ? "is-selected" : ""}`} key={document.id}>
            <button
              className="document-main"
              disabled={!selectable}
              onClick={() => onToggle(document.id)}
              title={selectable ? "Toggle document filter" : document.status}
              type="button"
            >
              <FileText size={18} />
              <span className="document-copy">
                <span className="document-name">{document.filename}</span>
                <span className="document-meta">
                  {statusIcon(document.status)}
                  {statusLabel(document)}
                </span>
              </span>
            </button>
            <button className="icon-button danger" onClick={() => onDelete(document.id)} title="Delete document" type="button">
              <Trash2 size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function statusIcon(status: DocumentRecord["status"]) {
  if (status === "processed") return <CheckCircle2 size={13} />;
  if (status === "failed") return <AlertTriangle size={13} />;
  if (status === "processing") return <Loader2 className="spin" size={13} />;
  return <Clock3 size={13} />;
}

function statusLabel(document: DocumentRecord) {
  if (document.status === "processed") return `${document.page_count}p / ${document.chunk_count} chunks`;
  if (document.status === "failed") return document.error_message ?? "Failed";
  return document.status;
}

