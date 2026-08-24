"""
ingest_docs.py
Module 5 (build step) -- reads the policy documents in docs/samples/,
splits them into chunks, embeds them locally with HuggingFace
all-MiniLM-L6-v2 (no API calls, no cost), and persists them to a Chroma
vector store on disk at ai-service/docs_vector_db/.

rag.py (the query side of Module 5) reads the vector store this script
builds. Run this file first, and re-run it any time a file in
docs/samples/ is added, removed or changed -- it always rebuilds from
scratch, so re-running is always safe.

Run:
    python ingest_docs.py
"""

import shutil
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ---------------------------------------------------------------------
# Config -- rag.py imports these so both files always agree on where the
# vector store lives and which embedding model/collection built it.
# ---------------------------------------------------------------------
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs" / "samples"
PERSIST_DIR = Path(__file__).resolve().parent / "docs_vector_db"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "policy_docs"

_LOADER_BY_SUFFIX = {
    ".txt": TextLoader,
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
}


# ---------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------

def _load_documents() -> List[Document]:
    """Load every supported file in docs/samples/ into LangChain Documents."""
    if not DOCS_DIR.exists():
        raise FileNotFoundError(
            f"{DOCS_DIR} does not exist. Put policy files (.txt/.pdf/.docx) there first."
        )

    files = sorted(p for p in DOCS_DIR.iterdir() if p.is_file())
    if not files:
        raise FileNotFoundError(f"No files found in {DOCS_DIR}.")

    docs: List[Document] = []
    for path in files:
        loader_cls = _LOADER_BY_SUFFIX.get(path.suffix.lower())
        if loader_cls is None:
            print(f"  Skipping {path.name} (unsupported file type '{path.suffix}')")
            continue

        print(f"  Loading {path.name} ...")
        if loader_cls is TextLoader:
            loaded = loader_cls(str(path), encoding="utf-8").load()
        else:
            loaded = loader_cls(str(path)).load()

        # Tag every chunk with just the filename, not the full disk path --
        # keeps citations readable and keeps the machine's folder layout out
        # of anything the LLM or the API response ever echoes back.
        for d in loaded:
            d.metadata["source"] = path.name
        docs.extend(loaded)

    return docs


# ---------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------

def build_vector_store() -> Chroma:
    """
    Load docs/samples/, split into chunks, embed, and persist to a fresh
    Chroma collection at ai-service/docs_vector_db/. Wipes any existing
    vector store at that path first.
    """
    print(f"Reading documents from {DOCS_DIR} ...")
    raw_docs = _load_documents()
    print(f"Loaded {len(raw_docs)} document/page section(s).")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(raw_docs)
    print(f"Split into {len(chunks)} chunk(s).")

    if PERSIST_DIR.exists():
        print(f"Removing existing vector store at {PERSIST_DIR} ...")
        shutil.rmtree(PERSIST_DIR)

    print(f"Embedding with {EMBEDDING_MODEL} (first run downloads the model, ~90MB) ...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(PERSIST_DIR),
    )
    print(f"Persisted {len(chunks)} chunk(s) to {PERSIST_DIR}")
    return vector_store


if __name__ == "__main__":
    build_vector_store()

    print("\n=== Smoke test: similarity search against the persisted store ===")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    for query in [
        "How long do I have to return a product?",
        "What is the warranty period for electronics?",
    ]:
        print(f"\nQuery: {query}")
        results = store.similarity_search(query, k=2)
        for r in results:
            print(f"  [{r.metadata.get('source')}] {r.page_content[:120]!r}...")
