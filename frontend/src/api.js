// Thin fetch wrapper for the PHP REST layer (backend-php/index.php).
// Base URL comes from frontend\.env.local (VITE_ prefix required by Vite).
// Example .env.local line:
//   VITE_API_BASE_URL=http://localhost:8080
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

async function postJson(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  let data
  try {
    data = await res.json()
  } catch {
    throw new Error(`Server returned non-JSON response (HTTP ${res.status})`)
  }

  if (!res.ok) {
    throw new Error(data?.detail || `Request failed (HTTP ${res.status})`)
  }

  return data
}

// Matches backend-php/index.php  POST /ask  -> FastAPI POST /ask
// Request:  { question: string }
// Response: { question, sql, columns: string[], rows: object[], row_count: number,
//              explanation: object|null, explanation_error: string|null }
export function askQuestion(question) {
  return postJson('/ask', { question })
}

// Matches backend-php/index.php  POST /ask-docs  -> FastAPI POST /ask-docs
// Request:  { question: string }
// Response: { question, answer: string, sources: string[] }
export function askDocs(question) {
  return postJson('/ask-docs', { question })
}
