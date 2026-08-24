
"""
tests/test_nl2sql.py
Unit tests for nl2sql.py's SQL sanity-checking logic.
 
These tests do NOT call the real Groq API -- call_llm is monkeypatched
in every test, so the suite runs offline, instantly, and for free.
 
Run from ai-service\\ (with the venv active):
    pytest tests\\test_nl2sql.py -v
"""
 
import sys
from pathlib import Path
 
import pytest
 
# Make sure `import nl2sql` works no matter which directory pytest is
# invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
 
import nl2sql
 
 
def test_strip_code_fences_removes_sql_fence():
    raw = "```sql\nSELECT 1;\n```"
    assert nl2sql._strip_code_fences(raw) == "SELECT 1;"
 
 
def test_strip_code_fences_removes_plain_fence():
    raw = "```\nSELECT 1;\n```"
    assert nl2sql._strip_code_fences(raw) == "SELECT 1;"
 
 
def test_strip_code_fences_noop_on_plain_sql():
    raw = "SELECT 1;"
    assert nl2sql._strip_code_fences(raw) == "SELECT 1;"
 
 
def test_nl_to_sql_accepts_clean_select(monkeypatch):
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "SELECT * FROM customers LIMIT 10;",
    )
    sql = nl2sql.nl_to_sql("List 10 customers")
    assert sql.lower().startswith("select")
    assert ";" not in sql
 
 
def test_nl_to_sql_accepts_with_clause(monkeypatch):
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "WITH t AS (SELECT 1 AS x) SELECT x FROM t;",
    )
    sql = nl2sql.nl_to_sql("Use a CTE")
    assert sql.lower().startswith("with")
 
 
def test_nl_to_sql_strips_markdown_fence(monkeypatch):
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "```sql\nSELECT * FROM products;\n```",
    )
    sql = nl2sql.nl_to_sql("List products")
    assert sql == "SELECT * FROM products"
 
 
def test_nl_to_sql_rejects_insert(monkeypatch):
    # Doesn't start with SELECT/WITH, so it's caught by that check first --
    # still rejected, just with a different message than the keyword scan.
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "INSERT INTO customers VALUES (1);",
    )
    with pytest.raises(nl2sql.NL2SQLError, match="did not return a SELECT"):
        nl2sql.nl_to_sql("Add a customer")
 
 
def test_nl_to_sql_rejects_forbidden_keyword_inside_select(monkeypatch):
    # Starts with SELECT, so it reaches the forbidden-keyword scan.
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "SELECT * INTO OUTFILE '/tmp/x' FROM customers",
    )
    with pytest.raises(nl2sql.NL2SQLError, match="forbidden keyword"):
        nl2sql.nl_to_sql("Dump customers to a file")
 
 
def test_nl_to_sql_rejects_multiple_statements(monkeypatch):
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "SELECT 1; SELECT 2;",
    )
    with pytest.raises(nl2sql.NL2SQLError, match="more than one"):
        nl2sql.nl_to_sql("Give me two results")
 
 
def test_nl_to_sql_rejects_empty_response(monkeypatch):
    monkeypatch.setattr(nl2sql, "call_llm", lambda prompt, system: "")
    with pytest.raises(nl2sql.NL2SQLError, match="empty"):
        nl2sql.nl_to_sql("Say nothing")
 
 
def test_nl_to_sql_honors_no_query_refusal(monkeypatch):
    monkeypatch.setattr(
        nl2sql, "call_llm",
        lambda prompt, system: "NO_QUERY: question is unrelated to this schema",
    )
    with pytest.raises(nl2sql.NL2SQLError, match="unrelated to this schema"):
        nl2sql.nl_to_sql("What's the weather today?")
 
 
def test_nl_to_sql_rejects_non_select_start(monkeypatch):
    monkeypatch.setattr(nl2sql, "call_llm", lambda prompt, system: "SHOW TABLES;")
    with pytest.raises(nl2sql.NL2SQLError, match="did not return a SELECT"):
        nl2sql.nl_to_sql("Show me the tables")
 
 
def test_nl_to_sql_rejects_blank_question():
    with pytest.raises(nl2sql.NL2SQLError, match="empty"):
        nl2sql.nl_to_sql("   ")
	