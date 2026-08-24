"""
tests/test_explain.py
Unit tests for explain.py's JSON-parsing and validation logic.

These tests do NOT call the real Groq API -- call_llm is monkeypatched
in every test, so the suite runs offline, instantly, and for free.

Run from ai-service\\ (with the venv active):
    pytest tests\\test_explain.py -v
"""

import sys
from pathlib import Path

import pytest

# Make sure `import explain` works no matter which directory pytest is
# invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import explain


_VALID_JSON = """{
  "summary": "Total revenue per region over the last 12 months, highest first.",
  "tables_used": ["orders", "customers", "regions", "order_items"],
  "filters": ["Excludes cancelled orders", "Only orders from the last 12 months"],
  "grouping": ["One row per region, revenue summed across all its orders"],
  "sorting": "Regions with the highest revenue first",
  "row_limit": null,
  "caveats": ["Freight charges are not included in this revenue figure"]
}"""


def test_strip_code_fences_removes_json_fence():
    raw = "```json\n{\"a\": 1}\n```"
    assert explain._strip_code_fences(raw) == '{"a": 1}'


def test_strip_code_fences_removes_plain_fence():
    raw = "```\n{\"a\": 1}\n```"
    assert explain._strip_code_fences(raw) == '{"a": 1}'


def test_strip_code_fences_noop_on_plain_json():
    raw = '{"a": 1}'
    assert explain._strip_code_fences(raw) == '{"a": 1}'


def test_explain_sql_accepts_valid_json(monkeypatch):
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: _VALID_JSON,
    )
    result = explain.explain_sql("SELECT * FROM orders")
    assert result["tables_used"] == ["orders", "customers", "regions", "order_items"]
    assert result["row_limit"] is None
    assert "revenue" in result["summary"].lower()


def test_explain_sql_accepts_json_with_code_fence(monkeypatch):
    fenced = f"```json\n{_VALID_JSON}\n```"
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: fenced,
    )
    result = explain.explain_sql("SELECT * FROM orders")
    assert result["tables_used"] == ["orders", "customers", "regions", "order_items"]


def test_explain_sql_fills_in_optional_defaults(monkeypatch):
    minimal = '{"summary": "Counts processing orders.", "tables_used": ["orders"]}'
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: minimal,
    )
    result = explain.explain_sql("SELECT COUNT(*) FROM orders")
    assert result["filters"] == []
    assert result["grouping"] == []
    assert result["sorting"] is None
    assert result["row_limit"] is None
    assert result["caveats"] == []


def test_explain_sql_rejects_empty_response(monkeypatch):
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: "",
    )
    with pytest.raises(explain.ExplainError, match="empty"):
        explain.explain_sql("SELECT * FROM orders")


def test_explain_sql_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: "not json at all",
    )
    with pytest.raises(explain.ExplainError, match="valid JSON"):
        explain.explain_sql("SELECT * FROM orders")


def test_explain_sql_rejects_json_missing_required_field(monkeypatch):
    missing_summary = '{"tables_used": ["orders"]}'
    monkeypatch.setattr(
        explain, "call_llm",
        lambda prompt, system, max_completion_tokens: missing_summary,
    )
    with pytest.raises(explain.ExplainError, match="expected shape"):
        explain.explain_sql("SELECT * FROM orders")


def test_explain_sql_rejects_blank_sql():
    with pytest.raises(explain.ExplainError, match="No SQL"):
        explain.explain_sql("   ")


def test_explain_sql_passes_question_into_prompt(monkeypatch):
    captured = {}

    def fake_call_llm(prompt, system, max_completion_tokens):
        captured["prompt"] = prompt
        return _VALID_JSON

    monkeypatch.setattr(explain, "call_llm", fake_call_llm)
    explain.explain_sql("SELECT * FROM orders", question="How many orders?")
    assert "How many orders?" in captured["prompt"]
    assert "SELECT * FROM orders" in captured["prompt"]
