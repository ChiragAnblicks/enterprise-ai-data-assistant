import { useState } from 'react'
import AskData from './components/AskData.jsx'
import ChatDocs from './components/ChatDocs.jsx'

const MODES = [
  { id: 'ask', label: 'Ask Data', component: AskData },
  { id: 'chat', label: 'Chat Docs', component: ChatDocs },
]

function App() {
  const [activeMode, setActiveMode] = useState('ask')
  const Active = MODES.find((m) => m.id === activeMode)?.component ?? AskData

  return (
    <div id="app-shell">
      <header>
        <h1>Enterprise AI Data Assistant</h1>
        <p className="hint">
          Ask a business question in plain English — get back the SQL, a
          short explanation, and the live results from the database. Or chat
          with the ingested policy documents.
        </p>
        <div className="model-badge">
          <span className="model-dot" />
          GROQ · GPT-OSS-20B
        </div>
      </header>

      <nav className="tabs">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={m.id === activeMode ? 'tab tab-active' : 'tab'}
            onClick={() => setActiveMode(m.id)}
          >
            {m.label}
          </button>
        ))}
      </nav>

      <main>
        <Active />
      </main>
    </div>
  )
}

export default App
