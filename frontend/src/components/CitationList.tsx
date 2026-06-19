import type { Citation } from "../types";

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (!citations.length) return null;
  const unique = citations.filter(
    (citation, index, list) =>
      list.findIndex((item) => item.document_id === citation.document_id && item.page_number === citation.page_number) === index
  );

  return (
    <div className="citation-list">
      {unique.map((citation) => (
        <button className="citation-chip" key={`${citation.chunk_id}-${citation.page_number}`} title={citation.text} type="button">
          <span>{citation.filename}</span>
          <strong>Page {citation.page_number}</strong>
        </button>
      ))}
    </div>
  );
}

