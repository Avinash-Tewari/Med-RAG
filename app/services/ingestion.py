"""Document ingestion pipeline — parse, chunk, embed, store in ChromaDB."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from app.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    UPLOAD_DIR,
)
from app.services.document_store import add_document

# ── Singletons ──────────────────────────────────────────────────────────
_embedding_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None

COLLECTION_NAME = "medical_docs"


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def get_collection() -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Parsers ─────────────────────────────────────────────────────────────

def _parse_pdf(file_path: Path) -> tuple[str, int]:
    """Parse a PDF and return (full_text, page_count)."""
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages), len(reader.pages)


def _parse_docx(file_path: Path) -> tuple[str, int]:
    """Parse a DOCX and return (full_text, paragraph_count_as_pages)."""
    from docx import Document

    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    # DOCX doesn't have true "pages", estimate by paragraph groups
    return "\n\n".join(paragraphs), max(1, len(paragraphs) // 20)


def _parse_txt(file_path: Path) -> tuple[str, int]:
    """Parse a TXT file and return (full_text, 1)."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return text, 1


PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".txt": _parse_txt,
}


# ── Main Ingestion ──────────────────────────────────────────────────────

def ingest_file(filename: str, file_bytes: bytes) -> dict:
    """
    Ingest an uploaded file into the RAG pipeline.

    1. Save to uploads/
    2. Parse text
    3. Chunk
    4. Embed & store in ChromaDB
    5. Track metadata

    Returns document metadata dict.
    """
    # Determine file extension
    ext = Path(filename).suffix.lower()
    if ext not in PARSERS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(PARSERS.keys())}"
        )

    # Save file to uploads directory
    save_path = UPLOAD_DIR / filename
    # Handle duplicate filenames
    counter = 1
    while save_path.exists():
        stem = Path(filename).stem
        save_path = UPLOAD_DIR / f"{stem}_{counter}{ext}"
        counter += 1
    save_path.write_bytes(file_bytes)

    # Parse
    full_text, page_count = PARSERS[ext](save_path)

    if not full_text.strip():
        raise ValueError("Document appears to be empty or could not be parsed.")

    # Chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(full_text)

    if not chunks:
        raise ValueError("No text chunks could be extracted from the document.")

    # Embed
    model = _get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    # Store in ChromaDB
    collection = get_collection()
    doc_id = add_document(
        filename=save_path.name,
        original_path=str(save_path),
        page_count=page_count,
        chunk_count=len(chunks),
    )

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": save_path.name,
            "chunk_index": i,
            "source": f"{save_path.name} — chunk {i + 1}/{len(chunks)}",
        }
        for i in range(len(chunks))
    ]

    # ChromaDB has a batch limit; insert in batches of 500
    batch_size = 500
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=chunks[start:end],
            metadatas=metadatas[start:end],
        )

    return {
        "id": doc_id,
        "filename": save_path.name,
        "page_count": page_count,
        "chunk_count": len(chunks),
        "status": "ingested",
    }


def delete_document_chunks(doc_id: str) -> None:
    """Remove all chunks belonging to a document from ChromaDB."""
    collection = get_collection()
    # Query all IDs for this doc
    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])
