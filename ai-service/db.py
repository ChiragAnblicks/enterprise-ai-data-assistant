"""
Module 3 - SQL execution + guard.
 
Takes a SQL string (normally produced by nl2sql.py), validates that it is a
single, read-only SELECT statement, enforces a row cap, and executes it
against MySQL using the read-only 'capstone_ro' user.
 
Run this file directly to smoke-test the guard and the DB connection:
    python db.py
"""
 
import os
import re
 
import mysql.connector
import sqlparse
from dotenv import load_dotenv, find_dotenv
 
# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
 
load_dotenv(find_dotenv())
 
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "CapstoneCore")
DB_RO_USER = os.getenv("DB_RO_USER", "capstone_ro")
DB_RO_PASSWORD = os.getenv("DB_RO_PASSWORD")
 
MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "200"))
QUERY_TIMEOUT_SECONDS = int(os.getenv("SQL_TIMEOUT_SECONDS", "10"))
 
# Keywords that must never appear in a query we execute, even inside a
# subquery or CTE. Checked as whole words so e.g. "DELETED_AT" doesn't match.
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "MERGE",
    "LOCK", "UNLOCK", "SET", "USE", "ATTACH", "DETACH", "VACUUM",
    "PRAGMA", "SHUTDOWN", "KILL", "LOAD_FILE", "OUTFILE", "DUMPFILE",
]
 
_FORBIDDEN_RE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in FORBIDDEN_KEYWORDS) + r")\b"
)
_LIMIT_RE = re.compile(r"(?i)\bLIMIT\s+(\d+)\s*(?:OFFSET\s+\d+)?\s*;?\s*$")
 
 
class SQLGuardError(ValueError):
    """Raised when a SQL statement fails validation and must not be run."""
 
 
# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------
 
def guard_sql(raw_sql: str) -> str:
    """
    Validate that raw_sql is a single SELECT statement and return a safe,
    row-capped version ready to execute. Raises SQLGuardError otherwise.
    """
    if not raw_sql or not raw_sql.strip():
        raise SQLGuardError("Empty SQL.")
 
    sql = raw_sql.strip()
 
    # Strip exactly one trailing semicolon (and trailing whitespace after it)
    sql = re.sub(r";\s*$", "", sql).strip()
 
    # 1) Must parse as exactly one statement.
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True)]
    if len(statements) != 1:
        raise SQLGuardError(
            f"Expected exactly 1 SQL statement, found {len(statements)}."
        )
    stmt = statements[0]
 
    # 2) First real keyword must be SELECT or WITH (a CTE feeding a SELECT).
    first_token = stmt.token_first(skip_cm=True)
    first_word = (first_token.value or "").upper() if first_token else ""
    if first_word not in ("SELECT", "WITH"):
        raise SQLGuardError(
            f"Only SELECT statements are allowed (got '{first_word}')."
        )
 
    # 3) No forbidden keywords anywhere in the statement (blocks write verbs,
    #    even inside a subquery, and blocks session/privilege changes).
    match = _FORBIDDEN_RE.search(sql)
    if match:
        raise SQLGuardError(f"Forbidden keyword '{match.group(1)}' in SQL.")
 
    # 4) No stacked statements smuggled in via a semicolon mid-string.
    if ";" in sql:
        raise SQLGuardError("Multiple statements are not allowed.")
 
    # 5) Row cap: rewrite an oversized LIMIT, or append one if missing.
    limit_match = _LIMIT_RE.search(sql)
    if limit_match:
        existing_limit = int(limit_match.group(1))
        if existing_limit > MAX_ROWS:
            sql = _LIMIT_RE.sub(f"LIMIT {MAX_ROWS}", sql)
    else:
        sql = f"{sql} LIMIT {MAX_ROWS}"
 
    return sql
 
 
# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
 
def _get_connection():
    if not DB_RO_PASSWORD:
        raise RuntimeError(
            "DB_RO_PASSWORD is not set. Add it to .env at the repo root."
        )
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_RO_USER,
        password=DB_RO_PASSWORD,
        database=DB_NAME,
        connection_timeout=5,
        autocommit=True,
    )
 
 
def execute_readonly_query(raw_sql: str) -> dict:
    """
    Guard, then run raw_sql against MySQL as capstone_ro.
    Returns {"sql": <sql actually run>, "columns": [...], "rows": [...],
    "row_count": int}.
    """
    safe_sql = guard_sql(raw_sql)
 
    conn = _get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            # Belt-and-suspenders server-side cap on execution time.
            cur.execute(
                f"SET SESSION MAX_EXECUTION_TIME={QUERY_TIMEOUT_SECONDS * 1000}"
            )
            cur.execute(safe_sql)
            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
    finally:
        conn.close()
 
    return {
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
 
 
# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    print("=== Guard tests (should all be rejected) ===")
    bad_queries = [
        "DROP TABLE customers",
        "SELECT * FROM customers; DROP TABLE customers",
        "UPDATE customers SET email='x' WHERE customer_id=1",
        "SELECT * FROM customers INTO OUTFILE '/tmp/x.csv'",
    ]
    for q in bad_queries:
        try:
            guard_sql(q)
            print(f"  FAIL (should have been rejected): {q}")
        except SQLGuardError as e:
            print(f"  OK rejected: {q!r} -> {e}")
 
    print("\n=== Guard row-cap test ===")
    capped = guard_sql("SELECT * FROM customers")
    print(f"  No LIMIT in input -> guarded SQL: {capped}")
    over_capped = guard_sql(f"SELECT * FROM customers LIMIT {MAX_ROWS + 1000}")
    print(f"  Oversized LIMIT -> guarded SQL: {over_capped}")
 
    print("\n=== Live query against MySQL (capstone_ro) ===")
    result = execute_readonly_query("SELECT * FROM customers")
    print(f"  SQL run: {result['sql']}")
    print(f"  Columns: {result['columns']}")
    print(f"  Row count returned: {result['row_count']} (cap is {MAX_ROWS})")
    if result["rows"]:
        print(f"  First row: {result['rows'][0]}")
