import { useState } from 'react'
import AskData from './components/AskData.jsx'
import ExplainSql from './components/ExplainSql.jsx'
import ChatDocs from './components/ChatDocs.jsx'

const MODES = [
  { id: 'ask', label: 'Ask Data', component: AskData },
  { id: 'explain', label: 'Explain SQL', component: ExplainSql },
  { id: 'chat', label: 'Chat Docs', component: ChatDocs },
]

function App() {
  const [activeMode, setActiveMode] = useState('ask')
  const Active = MODES.find((m) => m.id === activeMode)?.component ?? AskData

  return (
    <div id="app-shell">
      <header>
        <h1>Enterprise AI Data Assistant</h1>
        <p className="hint">Contoso Trading Services — capstone demo</p>
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
