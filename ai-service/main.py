"""
main.py
FastAPI app -- wires Module 2 (nl2sql), Module 3 (db), Module 4 (explain)
and Module 5 (rag) behind a single HTTP API.

Flow for POST /ask:
    question --nl_to_sql()--> sql --execute_readonly_query()--> rows
                                    \\--explain_sql()--> plain-English explanation

Flow for POST /ask-docs:
    question --answer_from_docs()--> answer grounded in docs/samples/*
    (requires `python ingest_docs.py` to have been run at least once)

Run:
    uvicorn main:app --reload --port 8000

Docs / manual test UI:
    http://127.0.0.1:8000/docs
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from nl2sql import nl_to_sql, NL2SQLError
from db import execute_readonly_query, SQLGuardError
from explain import explain_sql, ExplainError
from rag import answer_from_docs, RAGError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Enterprise AI Data Assistant", version="0.1.0")


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    explanation: Optional[dict] = None
    explanation_error: Optional[str] = None


class AskDocsRequest(BaseModel):
    question: str


class AskDocsResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip() if req.question else ""
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty.")

    # Module 2: English -> SQL
    try:
        sql = nl_to_sql(question)
    except NL2SQLError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Module 3: re-guard (independent security boundary) + execute as capstone_ro
    try:
        result = execute_readonly_query(sql)
    except SQLGuardError as e:
        # nl2sql already sanity-checks its own output; if db.py's stricter
        # guard still rejects it, treat that as "could not answer safely".
        raise HTTPException(
            status_code=422,
            detail=f"Generated SQL failed the safety guard: {e}",
        )
    except Exception as e:
        logger.exception("DB execution failed")
        raise HTTPException(status_code=502, detail=f"Database error: {e}")

    # Module 4: explain the SQL that was actually run (the guarded, row-capped
    # version) -- best-effort, so a flaky explanation never hides a working answer.
    explanation = None
    explanation_error = None
    try:
        explanation = explain_sql(result["sql"], question=question)
    except ExplainError as e:
        explanation_error = str(e)
        logger.warning("Explain failed: %s", e)

    return AskResponse(
        question=question,
        sql=result["sql"],
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
        explanation=explanation,
        explanation_error=explanation_error,
    )


@app.post("/ask-docs", response_model=AskDocsResponse)
def ask_docs(req: AskDocsRequest):
    question = req.question.strip() if req.question else ""
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty.")

    # Module 5: retrieve relevant chunks from docs/samples/ and answer,
    # grounded in those chunks, via the LLM.
    try:
        result = answer_from_docs(question)
    except RAGError as e:
        # At this point `question` is already known non-empty, so a RAGError
        # here means the document Q&A pipeline itself isn't ready (e.g.
        # `python ingest_docs.py` hasn't been run yet) or the model returned
        # nothing -- an operational problem, not something the user's
        # question caused.
        logger.exception("Document RAG failed")
        raise HTTPException(status_code=503, detail=f"Document Q&A unavailable: {e}")

    return AskDocsResponse(
        question=question,
        answer=result["answer"],
        sources=result["sources"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
