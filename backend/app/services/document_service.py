import logging
import uuid
from pathlib import Path

from app.database.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.rag.cleaner import TextCleaner
from app.rag.embeddings import GoogleEmbeddingClient
from app.rag.models import PageText
from app.rag.pdf_parser import PDFParser
from app.rag.splitter import RecursiveTokenTextSplitter
from app.rag.vector_store import ChromaVectorStore
from app.services.dependencies import get_embedding_client, get_vector_store

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(
        self,
        parser: PDFParser,
        cleaner: TextCleaner,
        splitter: RecursiveTokenTextSplitter,
        embeddings: GoogleEmbeddingClient,
        vector_store: ChromaVectorStore,
    ) -> None:
        self.parser = parser
        self.cleaner = cleaner
        self.splitter = splitter
        self.embeddings = embeddings
        self.vector_store = vector_store

    async def process_document(self, document_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if not document:
                logger.warning("Document %s was not found for processing", document_id)
                return

            document.status = DocumentStatus.processing
            document.error_message = None
            await session.commit()

            try:
                pages = self.parser.extract_pages(Path(document.storage_path))
                cleaned_pages = [
                    PageText(page_number=page.page_number, text=self.cleaner.clean(page.text))
                    for page in pages
                ]
                chunks = self.splitter.split_pages(
                    cleaned_pages,
                    filename=document.filename,
                    document_id=str(document.id),
                )
                embeddings = await self.embeddings.embed_documents([chunk.text for chunk in chunks])
                await self.vector_store.add_chunks(chunks, embeddings)

                document.status = DocumentStatus.processed
                document.page_count = len(pages)
                document.chunk_count = len(chunks)
                await session.commit()
                logger.info("Processed document %s into %s chunks", document.id, len(chunks))
            except Exception as exc:
                logger.exception("Document processing failed for %s", document.id)
                document.status = DocumentStatus.failed
                document.error_message = str(exc)[:2000]
                await session.commit()


def get_document_processor() -> DocumentProcessor:
    return DocumentProcessor(
        parser=PDFParser(),
        cleaner=TextCleaner(),
        splitter=RecursiveTokenTextSplitter(),
        embeddings=get_embedding_client(),
        vector_store=get_vector_store(),
    )


async def process_document_job(document_id: uuid.UUID) -> None:
    processor = get_document_processor()
    await processor.process_document(document_id)

