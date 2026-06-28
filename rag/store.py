from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    FILE_PATTERNS,
    embeddings_model,
)


def build_vector_store() -> Chroma:
    """Open the persistent Chroma collection; ingest sample_documents on first run."""
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings_model,
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )

    if vector_store._collection.count() == 0:
        loaders = [
            DirectoryLoader(DATA_DIR, glob=pattern, loader_cls=TextLoader, silent_errors=True)
            for pattern in FILE_PATTERNS
        ]
        docs = []
        for loader in loaders:
            docs.extend(loader.load())

        if not docs:
            raise ValueError(f"No documents found in {DATA_DIR} for patterns: {FILE_PATTERNS}")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            add_start_index=True,
        )
        vector_store.add_documents(splitter.split_documents(docs))

    return vector_store
