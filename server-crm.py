import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

from rag.agent import rag_agent
from rag.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    MAX_HISTORY_TURNS,
    embeddings_model,
)

app = FastAPI(title="RAG Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
tenant_vector_stores: dict[str, Chroma] = {}

HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]

CRM_API_BASE_URL = os.getenv("CRM_API_BASE_URL", "http://127.0.0.1:5237")
CRM_INTERNAL_API_KEY = os.getenv("CRM_INTERNAL_API_KEY", "replace-this-in-production")


class RetrievalDocument(BaseModel):
    id: int
    file_name: str = Field(alias="fileName")
    content: str
    company_id: int = Field(alias="companyId")


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    session_id: str | None = Field(default=None, alias="sessionId")
    company: str | None = None
    company_id: int = Field(alias="companyId")
    allowed_document_ids: list[int] = Field(default_factory=list, alias="allowedDocumentIds")
    tenant_index_name: str = Field(alias="tenantIndexName")


def _safe_collection_suffix(tenant_index_name: str) -> str:
    candidate = tenant_index_name.strip().lower()
    candidate = re.sub(r"[^a-z0-9_]+", "_", candidate)
    return candidate.strip("_") or "tenant"


def _tenant_store(tenant_index_name: str) -> Chroma:
    if tenant_index_name not in tenant_vector_stores:
        suffix = _safe_collection_suffix(tenant_index_name)
        tenant_vector_stores[tenant_index_name] = Chroma(
            collection_name=f"{COLLECTION_NAME}_{suffix}",
            embedding_function=embeddings_model,
            persist_directory=CHROMA_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return tenant_vector_stores[tenant_index_name]


def _chunk_documents(docs: list[Document]) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )

    sectioned: list[Document] = []
    for doc in docs:
        for section in header_splitter.split_text(doc.page_content):
            section.metadata = {**doc.metadata, **section.metadata}
            sectioned.append(section)

    return char_splitter.split_documents(sectioned)


def _fetch_documents_from_crm(company_id: int, document_ids: list[int]) -> list[RetrievalDocument]:
    query = urllib.parse.urlencode(
        {
            "companyId": company_id,
            "documentIds": [doc_id for doc_id in document_ids if doc_id > 0],
        },
        doseq=True,
    )
    endpoint = f"{CRM_API_BASE_URL.rstrip('/')}/files/internal/retrieval-documents?{query}"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/json",
            "X-Internal-Api-Key": CRM_INTERNAL_API_KEY,
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"CRM document fetch failed ({ex.code}): {body}") from ex
    except urllib.error.URLError as ex:
        raise RuntimeError("CRM document fetch failed: service unreachable") from ex

    raw = json.loads(body)
    if not isinstance(raw, list):
        raise RuntimeError("CRM document fetch returned an unexpected payload")
    return [RetrievalDocument.model_validate(item) for item in raw]


def _refresh_tenant_index(vector_store: Chroma, documents: list[RetrievalDocument]) -> None:
    try:
        vector_store._collection.delete(where={})
    except Exception:
        pass

    docs = [
        Document(
            page_content=doc.content,
            metadata={
                "source": doc.file_name,
                "company_id": doc.company_id,
                "file_id": doc.id,
            },
        )
        for doc in documents
        if doc.content.strip()
    ]

    chunks = _chunk_documents(docs)
    if chunks:
        vector_store.add_documents(chunks)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> dict[str, object]:
    message = req.message.strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    if req.company_id <= 0:
        return JSONResponse(status_code=400, content={"error": "companyId is required"})

    if not req.tenant_index_name.strip():
        return JSONResponse(status_code=400, content={"error": "tenantIndexName is required"})

    try:
        retrieval_documents = _fetch_documents_from_crm(req.company_id, req.allowed_document_ids)
    except RuntimeError as ex:
        return JSONResponse(status_code=502, content={"error": str(ex)})

    if not retrieval_documents:
        return JSONResponse(status_code=400, content={"error": "No CRM documents available for retrieval."})

    vector_store = _tenant_store(req.tenant_index_name)
    _refresh_tenant_index(vector_store, retrieval_documents)

    session_id = req.session_id or str(uuid.uuid4())
    session_key = f"{req.tenant_index_name}:{session_id}"
    history = sessions[session_key]

    output, standalone, top_score = rag_agent(message, history, vector_store)

    answer_for_history = output.split("\nSources:", 1)[0].strip()
    history.append((message, standalone, answer_for_history))
    if len(history) > MAX_HISTORY_TURNS:
        sessions[session_key] = history[-MAX_HISTORY_TURNS:]

    return {
        "sessionId": session_id,
        "answer": output,
        "topScore": top_score,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG CRM API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host for API server")
    parser.add_argument("--port", type=int, default=8000, help="Port for API server")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
