import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { api } from '../../api'
import { Card, CardHeader, CardTitle, Button } from '../ui'

interface Msg { role: 'user' | 'assistant'; content: string }

export default function QuickChat() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: 'assistant', content: 'Ready. Ask about positions, run analysis, or send a trade instruction.' },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = async () => {
    const text = input.trim()
    if (!text || sending) return
    setMsgs(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const ctx = msgs.slice(-8).map(m => ({ role: m.role, content: m.content }))
      const res = await api.chat(text, ctx)
      setMsgs(prev => [...prev, { role: 'assistant', content: res.reply }])
    } catch (e: unknown) {
      setMsgs(prev => [...prev, { role: 'assistant', content: `Error: ${e instanceof Error ? e.message : 'Unknown'}` }])
    }
    setSending(false)
  }

  return (
    <Card className="flex flex-col" padding="none">
      <div className="px-[var(--space-4)] pt-[var(--space-4)]">
        <CardHeader>
          <CardTitle subtitle="Natural language commands & trade execution">Trading Assistant</CardTitle>
        </CardHeader>
      </div>
      <div className="flex-1 overflow-y-auto px-[var(--space-4)] space-y-[var(--space-2)] max-h-[280px] min-h-[200px]">
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-[var(--space-2)] ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <Bot className="w-4 h-4 text-accent-green shrink-0 mt-0.5" />
            )}
            <div className={`text-xs leading-relaxed max-w-[85%] rounded-lg px-[var(--space-3)] py-[var(--space-2)] ${
              m.role === 'user'
                ? 'bg-accent-blue/10 border border-accent-blue/20 text-text'
                : 'bg-bg-elevated text-text'
            }`}>
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
            {m.role === 'user' && (
              <User className="w-4 h-4 text-accent-blue shrink-0 mt-0.5" />
            )}
          </div>
        ))}
        {sending && (
          <div className="flex gap-[var(--space-2)]">
            <Loader2 className="w-4 h-4 text-accent-green animate-spin shrink-0" />
            <span className="text-xs text-text-muted">Thinking...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="p-[var(--space-3)] border-t border-border/50 flex gap-[var(--space-2)]">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="e.g. BUY 100 AAPL MARKET, stop 180"
          className="flex-1 bg-bg-input border border-border rounded-lg px-[var(--space-3)] py-[var(--space-2)] text-xs placeholder:text-text-dim focus:border-accent-green/50"
          disabled={sending}
        />
        <Button size="sm" icon={<Send className="w-3.5 h-3.5" />}
          onClick={send} disabled={sending || !input.trim()} />
      </div>
    </Card>
  )
}

