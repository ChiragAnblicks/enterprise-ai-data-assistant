"""
Smoke test: proves the Groq API key works and the model responds.
Run with: python tests\test_llm_provider.py   (from ai-service\, venv active)
"""

import sys
from pathlib import Path

# Add ai-service/ (parent of this tests/ folder) to the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_provider import call_llm


def test_groq_smoke():
    reply = call_llm("Reply with exactly: GROQ_OK")
    print("Groq replied:", reply)
    assert "GROQ_OK" in reply


if __name__ == "__main__":
    test_groq_smoke()
    print("SMOKE TEST PASSED")
