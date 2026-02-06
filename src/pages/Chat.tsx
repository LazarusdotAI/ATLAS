import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { api } from '../api'
import { Card, Button } from '../components/ui'

interface Msg { role: 'user' | 'assistant'; content: string; ts: string }

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'assistant', content: 'StockBotFree ready. Give me a trade instruction or ask about your account.', ts: new Date().toLocaleTimeString() },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || sending) return
    const userMsg: Msg = { role: 'user', content: text, ts: new Date().toLocaleTimeString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)
    try {
      const ctx = messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
      const res = await api.chat(text, ctx)
      setMessages(prev => [...prev, { role: 'assistant', content: res.reply, ts: new Date().toLocaleTimeString() }])
    } catch (e: unknown) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e instanceof Error ? e.message : 'Unknown'}`, ts: new Date().toLocaleTimeString() }])
    }
    setSending(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-[var(--space-4)]">
        <h2 className="text-lg font-bold">Trading Chat</h2>
        <p className="text-xs text-text-dim">Send trade instructions or ask questions about your portfolio</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-[var(--space-3)] pr-[var(--space-2)]">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-[var(--space-3)] ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="w-icon-box-md h-icon-box-md rounded-lg bg-accent-green/10 flex items-center justify-center shrink-0 mt-[var(--space-1)]">
                <Bot className="w-icon-md h-icon-md text-accent-green" />
              </div>
            )}
            <Card
              variant={m.role === 'user' ? 'ghost' : 'default'}
              padding="none"
              className={`max-w-[70%] px-[var(--space-4)] py-[var(--space-3)] text-sm leading-relaxed
                ${m.role === 'user'
                  ? 'bg-accent-blue/10 border border-accent-blue/20 text-text rounded-xl'
                  : 'text-text'}`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              <div className="text-2xs text-text-dim mt-[var(--space-1-5)]">{m.ts}</div>
            </Card>
            {m.role === 'user' && (
              <div className="w-icon-box-md h-icon-box-md rounded-lg bg-accent-blue/10 flex items-center justify-center shrink-0 mt-[var(--space-1)]">
                <User className="w-icon-md h-icon-md text-accent-blue" />
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="flex gap-[var(--space-3)]">
            <div className="w-icon-box-md h-icon-box-md rounded-lg bg-accent-green/10 flex items-center justify-center shrink-0">
              <Loader2 className="w-icon-md h-icon-md text-accent-green animate-spin" />
            </div>
            <Card padding="none" className="px-[var(--space-4)] py-[var(--space-3)] text-sm text-text-muted">
              Thinking...
            </Card>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-[var(--space-4)] flex gap-[var(--space-3)]">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="e.g. BUY 100 AAPL MARKET, stop 180, target 195"
          className="flex-1 bg-bg-input border border-border rounded-xl px-[var(--space-4)] py-[var(--space-3)] text-sm placeholder:text-text-dim focus:border-accent-green/50"
          disabled={sending}
        />
        <Button
          variant="primary"
          size="lg"
          icon={<Send className="w-icon-md h-icon-md" />}
          onClick={send}
          disabled={sending || !input.trim()}
        >
          Send
        </Button>
      </div>
    </div>
  )
}

