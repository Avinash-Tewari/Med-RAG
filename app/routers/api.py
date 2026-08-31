"""API router — upload documents, query the RAG pipeline, manage documents."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services import document_store, ingestion, reasoning

router = APIRouter(prefix="/api", tags=["api"])


# ── Schemas ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    has_answer: bool
    reasoning_steps: list[str]
    answer: str
    citations: list[dict]
    confidence: str
    confidence_reason: str
    sources_used: list[dict]


# ── Endpoints ───────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a medical document (PDF, DOCX, or TXT) for ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    try:
        file_bytes = await file.read()
        result = ingestion.ingest_file(file.filename, file_bytes)
        return {"status": "success", "document": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    """Ask a medical question. Returns grounded answer with citations."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = reasoning.query(req.question)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}",
        )


@router.get("/documents")
async def list_documents():
    """List all uploaded documents."""
    docs = document_store.list_documents()
    return {"documents": docs}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its chunks from the vector store."""
    doc = document_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove chunks from ChromaDB
    try:
        ingestion.delete_document_chunks(doc_id)
    except Exception:
        pass  # Best-effort cleanup

    # Remove metadata
    document_store.delete_document(doc_id)

    # Remove uploaded file
    from pathlib import Path
    file_path = Path(doc.get("original_path", ""))
    if file_path.exists():
        file_path.unlink()

    return {"status": "deleted", "document_id": doc_id}
