"""
nl2sql.py
Module 2 -- English -> SQL.
 
Turns a plain-English business question into a single read-only MySQL
SELECT statement, grounded in docs/schema_context.md.
 
Scope note: this module only GENERATES and lightly sanity-checks SQL
text. It does not execute anything against the database and it is not
the security boundary -- that is db.py (Module 3), which must
independently re-validate and row-cap every statement before it ever
runs against capstone_ro. Treat the checks below as "catch obvious LLM
mistakes early", not as the security layer.
"""
 
import re
from pathlib import Path
 
from llm_provider import call_llm
 
# ---------------------------------------------------------------------
# Schema context (loaded once, at import time, from the repo's docs/ folder)
# ---------------------------------------------------------------------
_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "docs" / "schema_context.md"
 
 
def _load_schema_context() -> str:
    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema context not found at {_SCHEMA_PATH}. "
            "Module 2 needs docs/schema_context.md to ground the SQL it generates."
        )
    return _SCHEMA_PATH.read_text(encoding="utf-8")
 
 
_SCHEMA_CONTEXT = _load_schema_context()
 
_SYSTEM_PROMPT = f"""You are a MySQL 8 query generator for the CapstoneCore database.
 
Follow the schema, business rules and MySQL dialect rules below exactly.
They are the only source of truth about table names, column names and
how to compute business terms like "revenue" or "sales".
 
{_SCHEMA_CONTEXT}
 
Output rules -- follow all of these:
1. Output ONE single MySQL SELECT statement and nothing else.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE,
   REPLACE, GRANT, CALL, or multiple statements separated by ';'.
3. Do not wrap the SQL in markdown code fences, do not add commentary,
   do not explain the query. Return raw SQL text only.
4. Always use explicit JOIN ... ON with short table aliases, as shown in
   the join map.
5. If the question is ambiguous or cannot be answered from this schema,
   return exactly: NO_QUERY: <one short sentence saying why>
6. If the question does not include a row limit and could return many
   rows (e.g. "list", "show all"), add "LIMIT 200".
"""
 
_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "replace", "grant", "revoke", "call", "merge",
    "exec", "execute", "into outfile", "load_file",
)
 
 
class NL2SQLError(Exception):
    """Raised when the LLM cannot, or refuses to, produce safe SQL."""
 
 
def _strip_code_fences(text: str) -> str:
    """Remove ```sql ... ``` or ``` ... ``` wrappers if the model added them anyway."""
    text = text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
 
 
def _sanity_check(sql: str) -> None:
    """Raise NL2SQLError if the response is not a single, safe-looking SELECT."""
    if sql.upper().startswith("NO_QUERY"):
        reason = sql.split(":", 1)[-1].strip() if ":" in sql else ""
        raise NL2SQLError(reason or "Model could not answer this question from this schema.")
 
    if not sql:
        raise NL2SQLError("Model returned an empty response.")
 
    stripped = sql.rstrip(";").strip()
    if ";" in stripped:
        raise NL2SQLError("Model returned more than one SQL statement.")
 
    words = stripped.split(None, 1)
    first_word = words[0].lower() if words else ""
    if first_word not in ("select", "with"):
        raise NL2SQLError(f"Model did not return a SELECT statement (got: {sql[:60]!r}).")
 
    lowered = stripped.lower()
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", lowered):
            raise NL2SQLError(f"Generated SQL contains a forbidden keyword: '{kw}'.")
 
 
def nl_to_sql(question: str) -> str:
    """
    Convert a plain-English question into a single read-only MySQL
    SELECT statement (as a string, no trailing semicolon).
 
    Raises NL2SQLError if the model refuses, or returns something that
    is not a single, safe-looking SELECT/WITH statement.
    """
    if not question or not question.strip():
        raise NL2SQLError("Question is empty.")
 
    raw = call_llm(prompt=question.strip(), system=_SYSTEM_PROMPT)
    sql = _strip_code_fences(raw)
    _sanity_check(sql)
    return sql.rstrip(";").strip()
 
 
if __name__ == "__main__":
    _test_questions = [
        "What were total sales by region last year?",
        "List the top 5 customers by net revenue.",
        "How many orders are still in Processing status?",
    ]
    for q in _test_questions:
        print(f"\nQ: {q}")
        try:
            sql = nl_to_sql(q)
            print(f"SQL:\n{sql}")
        except NL2SQLError as e:
            print(f"REFUSED: {e}")
