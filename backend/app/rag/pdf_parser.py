from pathlib import Path

import fitz

from app.rag.models import PageText


class PDFParser:
    """Extract page-level text from PDFs with PyMuPDF."""

    def extract_pages(self, path: str | Path) -> list[PageText]:
        pages: list[PageText] = []
        with fitz.open(path) as document:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text", sort=True)
                pages.append(PageText(page_number=page_index, text=text))
        return pages

