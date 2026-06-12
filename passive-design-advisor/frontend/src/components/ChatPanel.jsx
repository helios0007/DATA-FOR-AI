import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

/**
 * ChatPanel — Streaming chat with Claude, grounded in the analysis report.
 * Props: sessionId, analysisResult
 */
export default function ChatPanel({ sessionId, analysisResult }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I can answer questions about the analysis results for your building. What would you like to know?',
    },
  ])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const buildReportContext = () => {
    if (!analysisResult) return null
    const { diagnosis, strategies, site } = analysisResult
    if (!diagnosis) return null
    const strats = strategies?.map(s =>
      `${s.name.replace(/_/g,' ')}: ${s.impact_level} (${s.impact_score.toFixed(0)}/100) — ${s.precondition_met}`
    ).join('\n')
    return (
      `Overheating risk: ${diagnosis.risk_level} (proxy ODH = ${diagnosis.proxy_odh?.toFixed(2)})\n` +
      `Thermal comfort zone: ${site?.thermal_comfort_gridcode} — ${site?.thermal_comfort_label}\n` +
      `July diurnal swing: ${site?.july_diurnal_swing_C?.toFixed(1)}°C\n` +
      `Strategies:\n${strats}`
    )
  }

  const send = async () => {
    if (!input.trim() || loading || !sessionId) return
    const userMsg = { role: 'user', content: input.trim() }
    const history = [...messages, userMsg]
    setMessages(history)
    setInput('')
    setLoading(true)

    // Add empty assistant bubble to stream into
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    const setLastMessage = updater =>
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = updater(updated[updated.length - 1])
        return updated
      })

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          messages: history,
          report_context: buildReportContext(),
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Chat request failed (HTTP ${res.status})`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()   // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const evt = JSON.parse(data)
            if (evt.error) throw new Error(evt.error)
            if (evt.text) {
              setLastMessage(m => ({ role: 'assistant', content: m.content + evt.text }))
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue   // partial JSON — skip
            throw e
          }
        }
      }
    } catch (e) {
      setLastMessage(() => ({ role: 'assistant', content: `⚠ ${e.message}` }))
    }
    setLoading(false)
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              className={m.role === 'assistant' ? 'md-body' : undefined}
              style={{
                maxWidth: '80%',
                padding: '8px 12px',
                borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                background: m.role === 'user' ? 'var(--accent)' : 'var(--surface2)',
                color: m.role === 'user' ? '#fff' : 'var(--text)',
                fontSize: 13,
                lineHeight: 1.6,
                whiteSpace: m.role === 'user' ? 'pre-wrap' : 'normal',
              }}
            >
              {m.role === 'assistant'
                ? (m.content
                    ? <ReactMarkdown>{m.content}</ReactMarkdown>
                    : (loading && i === messages.length - 1
                        ? <span style={{ color: 'var(--text-dim)' }}>▌</span>
                        : ''))
                : m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder={sessionId ? 'Ask about the analysis…' : 'Run an analysis first to enable chat'}
          disabled={!sessionId || loading}
          rows={2}
          style={{
            flex: 1, resize: 'none', background: 'var(--surface2)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius)',
            color: 'var(--text)', fontFamily: 'var(--font)', fontSize: 13,
            padding: '6px 10px', outline: 'none',
          }}
        />
        <button
          className="btn-primary"
          onClick={send}
          disabled={!input.trim() || loading || !sessionId}
          style={{ alignSelf: 'flex-end' }}
        >
          {loading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
