from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    FILE_PATTERNS,
    embeddings_model,
)

HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]


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

        # 1) split each markdown doc along its header structure, capturing the heading path
        #    as metadata (h1/h2/h3). 2) cap any oversized section with a character splitter.
        header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
        char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            add_start_index=True,
        )

        sectioned = []
        for doc in docs:
            for section in header_splitter.split_text(doc.page_content):
                section.metadata = {**doc.metadata, **section.metadata}
                sectioned.append(section)

        chunks = char_splitter.split_documents(sectioned)
        vector_store.add_documents(chunks)

    return vector_store
