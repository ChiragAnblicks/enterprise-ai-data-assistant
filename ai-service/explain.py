"""
explain.py
Module 4 -- structured SQL explanation.

Takes a SQL SELECT statement (normally the output of nl2sql.py) and asks the
LLM to explain, in plain English, what it does -- grounded in the same
docs/schema_context.md used by Module 2, so table/column meanings and
business-rule wording (e.g. "line revenue", "net revenue") stay consistent
with how the SQL was generated.

Scope note: this module only explains SQL text, it does not execute it and
it is not a security check. db.py (Module 3) is still the only thing that
guards and runs a query against MySQL.

Run this file directly to smoke-test it against a few sample queries:
    python explain.py
"""

import json
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ValidationError

from llm_provider import call_llm

# ---------------------------------------------------------------------
# Schema context (same file nl2sql.py uses, so explanations describe
# tables/columns the same way the SQL was generated from)
# ---------------------------------------------------------------------
_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "docs" / "schema_context.md"


def _load_schema_context() -> str:
    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema context not found at {_SCHEMA_PATH}. "
            "Module 4 needs docs/schema_context.md to describe tables/columns correctly."
        )
    return _SCHEMA_PATH.read_text(encoding="utf-8")


_SCHEMA_CONTEXT = _load_schema_context()

_SYSTEM_PROMPT = f"""You are explaining MySQL 8 SELECT statements written against the
CapstoneCore database, for a non-technical business user who is deciding whether to
trust and run the query. Use the schema below as the only source of truth about what
tables and columns mean.

{_SCHEMA_CONTEXT}

Output rules -- follow all of these:
1. Output ONE JSON object and nothing else. No markdown code fences, no commentary
   before or after it.
2. The JSON object must have exactly these keys:
   - "summary": one or two plain-English sentences describing what the query returns.
   - "tables_used": list of table names (strings) the query reads from.
   - "filters": list of plain-English descriptions of each WHERE/HAVING condition.
     Empty list if there are none.
   - "grouping": list of plain-English descriptions of GROUP BY / aggregation logic.
     Empty list if there are none.
   - "sorting": one plain-English sentence describing ORDER BY, or null if there is none.
   - "row_limit": the integer from LIMIT, or null if there is none.
   - "caveats": list of short warnings a business user should know (e.g. cancelled
     orders excluded, refunds not netted out, discontinued products included, a
     column name that doesn't match what it actually computes).
     Empty list if there are none.
3. Do not invent tables, columns or business rules that are not in the schema above.
4. Keep "summary" free of SQL syntax -- describe it the way you'd explain it to
   someone who has never written a query.
"""


class SQLExplanation(BaseModel):
    summary: str
    tables_used: List[str]
    filters: List[str] = []
    grouping: List[str] = []
    sorting: Optional[str] = None
    row_limit: Optional[int] = None
    caveats: List[str] = []


class ExplainError(Exception):
    """Raised when the LLM cannot, or refuses to, produce a valid explanation."""


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if the model added them anyway."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def explain_sql(sql: str, question: Optional[str] = None) -> dict:
    """
    Ask the LLM to explain a single SQL SELECT statement in plain English.

    `question` is the original natural-language question (optional). If given,
    it's passed along purely as context so the summary reads more naturally --
    it never changes what SQL is being explained.

    Returns a dict with keys: summary, tables_used, filters, grouping,
    sorting, row_limit, caveats.

    Raises ExplainError if sql is empty, or if the model's response is empty
    or is not valid JSON matching that shape.
    """
    if not sql or not sql.strip():
        raise ExplainError("No SQL to explain.")

    prompt = f"SQL to explain:\n{sql.strip()}"
    if question and question.strip():
        prompt = f"Original question: {question.strip()}\n\n{prompt}"

    # openai/gpt-oss-20b is a reasoning model (see llm_provider.py) -- this
    # prompt asks for several structured fields at once, so it needs more
    # headroom than the 2048-token default or the JSON can come back empty
    # or truncated mid-object.
    raw = call_llm(
        prompt=prompt,
        system=_SYSTEM_PROMPT,
        max_completion_tokens=4096,
    )

    if not raw or not raw.strip():
        raise ExplainError("Model returned an empty response.")

    cleaned = _strip_code_fences(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ExplainError(f"Model did not return valid JSON: {e}") from e

    try:
        explanation = SQLExplanation(**data)
    except ValidationError as e:
        raise ExplainError(f"Model's JSON did not match the expected shape: {e}") from e

    return explanation.model_dump()


if __name__ == "__main__":
    _test_queries = [
        (
            "SELECT r.region_name, ROUND(SUM(oi.quantity * oi.unit_price * "
            "(1 - oi.discount_pct / 100)), 2) AS revenue "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.customer_id "
            "JOIN regions r ON c.region_id = r.region_id "
            "JOIN order_items oi ON oi.order_id = o.order_id "
            "WHERE o.order_status <> 'Cancelled' "
            "AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH) "
            "GROUP BY r.region_name "
            "ORDER BY revenue DESC",
            "What were total sales by region over the last year?",
        ),
        (
            "SELECT c.customer_name, "
            "ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100)), 2) "
            "AS revenue "
            "FROM customers c "
            "JOIN orders o ON o.customer_id = c.customer_id "
            "JOIN order_items oi ON oi.order_id = o.order_id "
            "WHERE o.order_status <> 'Cancelled' "
            "GROUP BY c.customer_name "
            "ORDER BY revenue DESC "
            "LIMIT 5",
            "List the top 5 customers by revenue.",
        ),
        (
            "SELECT COUNT(*) AS processing_orders FROM orders "
            "WHERE order_status = 'Processing'",
            "How many orders are still in Processing status?",
        ),
    ]

    for sql, question in _test_queries:
        print(f"\nQ: {question}")
        print(f"SQL:\n{sql}")
        try:
            explanation = explain_sql(sql, question=question)
            print("Explanation:")
            print(json.dumps(explanation, indent=2))
        except ExplainError as e:
            print(f"FAILED: {e}")
