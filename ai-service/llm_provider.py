"""
llm_provider.py
Only file in this project that imports a vendor LLM SDK (Groq).
Every other module calls call_llm() from here.
"""
 
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
 
# Load .env from the repo root (one level up from this file)
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)
 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"
 
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Check that .env exists at the repo root "
        "and contains GROQ_API_KEY=your_key"
    )
 
_client = Groq(api_key=GROQ_API_KEY)
 
 
def call_llm(
    prompt: str,
    system: str = "You are a helpful assistant.",
    reasoning_effort: str = "low",
    max_completion_tokens: int = 2048,
) -> str:
    """
    Send a single prompt to Groq and return the text response.
 
    openai/gpt-oss-20b is a reasoning model: it spends part of its token
    budget "thinking" before it writes the final answer into `content`.
    Groq's default max_completion_tokens is only 1024, which is enough
    for simple prompts but can be exhausted mid-reasoning on harder ones
    -- when that happens `content` comes back empty even though the API
    call itself succeeded. reasoning_effort="low" keeps the thinking
    phase short, and max_completion_tokens=2048 leaves headroom for both
    the reasoning and the actual answer. If you see empty responses again
    on more complex prompts later (e.g. in explain.py), raise
    max_completion_tokens further (4096+) for that call.
    """
    response = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        reasoning_effort=reasoning_effort,
        max_completion_tokens=max_completion_tokens,
    )
    return response.choices[0].message.content
 
 
if __name__ == "__main__":
    reply = call_llm("Reply with exactly: GROQ_OK")
    print(reply)
