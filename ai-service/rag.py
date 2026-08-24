"""
rag.py
Module 5 -- document Q&A over the policy documents in docs/samples/.

Reads the Chroma vector store built by ingest_docs.py, retrieves the most
relevant chunks for a question, and asks the LLM to answer using only
those chunks -- so answers are grounded in the actual policy text instead
of the model's own guesses.

Scope note: like nl2sql.py/explain.py, this module only reasons over text.
It never touches MySQL and it is not a security boundary.

Prerequisite: run `python ingest_docs.py` at least once before this file
will find anything -- it raises RAGError immediately if the vector store
is missing.

Run this file directly to smoke-test it against a few sample questions:
    python rag.py
"""

from typing import List

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from llm_provider import call_llm
from ingest_docs import EMBEDDING_MODEL, COLLECTION_NAME, PERSIST_DIR

TOP_K = 4

_SYSTEM_PROMPT = """You are answering questions about Contoso Trading Services'
policy documents (returns, warranty, sales and pricing) for a business user.

Rules -- follow all of these:
1. Answer ONLY using the excerpts provided below the question. Do not use
   outside knowledge and do not guess at policy details that aren't in the
   excerpts.
2. If the excerpts don't contain enough information to answer, say so
   plainly -- reply with exactly: "I couldn't find that in the policy
   documents provided." Do not invent an answer.
3. Keep the answer to a few plain sentences. No markdown, no bullet points.
4. When useful, say which document the answer came from (e.g. "Per the
   Returns and Refunds Policy, ...").
"""


class RAGError(Exception):
    """Raised when the document Q&A pipeline cannot produce an answer."""


_embeddings = None
_store = None


def _get_store() -> Chroma:
    """Lazily open the persisted Chroma store (loaded once per process)."""
    global _embeddings, _store
    if _store is not None:
        return _store

    if not PERSIST_DIR.exists():
        raise RAGError(
            f"No vector store found at {PERSIST_DIR}. "
            "Run `python ingest_docs.py` first to build it."
        )

    _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    _store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    return _store


def _format_context(chunks) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        source = c.metadata.get("source", "unknown")
        parts.append(f"[Excerpt {i} - {source}]\n{c.page_content}")
    return "\n\n".join(parts)


def answer_from_docs(question: str, k: int = TOP_K) -> dict:
    """
    Answer a plain-English question using the ingested policy documents.

    Returns {"answer": str, "sources": [<filename>, ...]} -- sources are
    the deduplicated, ordered list of document filenames the retrieved
    chunks came from (regardless of whether the model actually cited them
    in the answer text).

    Raises RAGError if the question is empty, the vector store hasn't been
    built yet (run ingest_docs.py), or the model returns an empty response.
    """
    if not question or not question.strip():
        raise RAGError("Question is empty.")

    store = _get_store()
    chunks = store.similarity_search(question.strip(), k=k)

    if not chunks:
        return {
            "answer": "I couldn't find that in the policy documents provided.",
            "sources": [],
        }

    context = _format_context(chunks)
    prompt = f"Question: {question.strip()}\n\nExcerpts:\n{context}"

    raw = call_llm(prompt=prompt, system=_SYSTEM_PROMPT)

    if not raw or not raw.strip():
        raise RAGError("Model returned an empty response.")

    sources: List[str] = []
    for c in chunks:
        name = c.metadata.get("source", "unknown")
        if name not in sources:
            sources.append(name)

    return {"answer": raw.strip(), "sources": sources}


if __name__ == "__main__":
    _test_questions = [
        "How many days do I have to return a product?",
        "What is the warranty period for electronics?",
        "Is there a loyalty rewards program for repeat customers?",  # not in any doc
    ]
    for q in _test_questions:
        print(f"\nQ: {q}")
        try:
            result = answer_from_docs(q)
            print(f"A: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except RAGError as e:
            print(f"FAILED: {e}")
