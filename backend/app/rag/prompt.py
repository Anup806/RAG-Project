from app.rag.models import RetrievedChunk


SYSTEM_INSTRUCTION = """You are a PDF knowledge assistant.
Answer only from the supplied document context.
If the context does not contain the answer, say that the uploaded documents do not contain enough information.
Do not use outside knowledge.
Use concise, direct prose.
Do not invent citations, filenames, or page numbers.
The application appends a verified Sources section from retrieved metadata."""


def build_rag_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[S{index}] File: {chunk.filename}\n"
            f"Page: {chunk.page_number}\n"
            f"Chunk ID: {chunk.chunk_id}\n"
            f"Text:\n{chunk.text}"
        )
    context = "\n\n---\n\n".join(context_blocks)
    return (
        "Use the following retrieved PDF excerpts to answer the user's question.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer with grounded claims only. Do not add a separate Sources section."
    )


def format_sources(sources: list[dict[str, str | int]]) -> str:
    if not sources:
        return "Sources:\n- None"

    seen: set[tuple[str, int]] = set()
    lines = ["Sources:"]
    for source in sources:
        filename = str(source["filename"])
        page_number = int(source["page_number"])
        key = (filename, page_number)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {filename}\n  Page: {page_number}")
    return "\n".join(lines)


def append_source_footer(answer: str, sources: list[dict[str, str | int]]) -> str:
    return f"{answer.rstrip()}\n\n{format_sources(sources)}"
