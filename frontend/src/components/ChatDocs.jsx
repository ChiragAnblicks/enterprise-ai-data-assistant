import { useState } from 'react'
import { askDocs } from '../api.js'

export default function ChatDocs() {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([]) // { role: 'user' | 'assistant', content: string, sources?: string[] }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    const text = message.trim()
    if (!text || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setMessage('')
    setLoading(true)
    setError(null)

    try {
      // Backend is stateless per-question (no conversation history param on
      // POST /ask-docs) -- each question is answered independently against
      // the document store.
      const data = await askDocs(text)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer, sources: data.sources },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <h2>Chat with your documents</h2>
      <p className="hint">
        Ask questions about the policy documents you have uploaded and
        ingested into the vector store.
      </p>

      <div className="chat-log">
        {messages.length === 0 && <p className="hint">No messages yet.</p>}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role}`}>
            <strong>{m.role === 'user' ? 'You' : 'Assistant'}:</strong>{' '}
            <span>{m.content}</span>
            {m.sources && m.sources.length > 0 && (
              <div className="hint">Sources: {m.sources.join(', ')}</div>
            )}
          </div>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit} className="stack">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g. What is the return policy for damaged products?"
          rows={2}
        />
        <button type="submit" disabled={loading || !message.trim()}>
          {loading ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
