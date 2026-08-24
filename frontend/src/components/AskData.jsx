import { useState } from 'react'
import { askQuestion } from '../api.js'

// FastAPI's explain.py returns a "structured" explanation as a JSON object,
// not a fixed set of fields, so this renders whatever keys it contains
// instead of assuming a specific shape.
function ExplanationBlock({ data }) {
  if (data == null) return null

  if (typeof data === 'string') {
    return <p>{data}</p>
  }

  if (Array.isArray(data)) {
    return (
      <ul>
        {data.map((item, i) => (
          <li key={i}>{typeof item === 'object' ? JSON.stringify(item) : String(item)}</li>
        ))}
      </ul>
    )
  }

  if (typeof data === 'object') {
    return (
      <dl className="explanation-list">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="explanation-row">
            <dt>{key.replace(/_/g, ' ')}</dt>
            <dd>
              {Array.isArray(value)
                ? value.join(', ')
                : typeof value === 'object' && value !== null
                  ? JSON.stringify(value)
                  : String(value)}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  return <p>{String(data)}</p>
}

export default function AskData() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!question.trim() || loading) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await askQuestion(question.trim())
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <h2>Ask a question about your data</h2>
      <p className="hint">
        Type a plain-English question. It is converted to a read-only SQL
        SELECT, run against CapstoneCore, and explained below.
      </p>

      <form onSubmit={handleSubmit} className="stack">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which 5 customers placed the most orders in 2025?"
          rows={3}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="result stack">
          {result.sql && (
            <div>
              <h3>Generated SQL</h3>
              <pre>{result.sql}</pre>
            </div>
          )}

          {Array.isArray(result.rows) && (
            <div>
              <h3>
                Results ({result.row_count ?? result.rows.length} row
                {(result.row_count ?? result.rows.length) === 1 ? '' : 's'})
              </h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {(result.columns || []).map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i}>
                        {(result.columns || []).map((col) => (
                          <td key={col}>{String(row[col])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.explanation != null && (
            <div>
              <h3>Explanation</h3>
              <ExplanationBlock data={result.explanation} />
            </div>
          )}

          {result.explanation_error && (
            <p className="hint">
              (Explanation unavailable: {result.explanation_error})
            </p>
          )}
        </div>
      )}
    </div>
  )
}
