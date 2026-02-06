import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Card, Button, Badge, FilterBar, DataTable, type Column } from '../components/ui'

type Order = Record<string, unknown>

const FILTER_OPTIONS = [
  { id: 'all', label: 'All' },
  { id: 'open', label: 'Open' },
  { id: 'closed', label: 'Closed' },
  { id: 'filled', label: 'Filled' },
  { id: 'cancelled', label: 'Cancelled' },
]

function sideColor(side: string): 'green' | 'red' | 'dim' {
  return side.toLowerCase() === 'buy' ? 'green' : side.toLowerCase() === 'sell' ? 'red' : 'dim'
}

function statusColor(status: string): 'green' | 'red' | 'amber' | 'dim' {
  const s = status.toLowerCase()
  if (s === 'filled') return 'green'
  if (s === 'cancelled') return 'red'
  if (s === 'new' || s === 'open' || s === 'partially_filled') return 'amber'
  return 'dim'
}

const orderColumns: Column<Order>[] = [
  { key: 'symbol', header: 'Symbol', render: (o) => <span className="font-semibold text-text">{String(o.symbol ?? '—')}</span> },
  { key: 'side', header: 'Side', render: (o) => { const v = String(o.side ?? '—'); return <Badge color={sideColor(v)}>{v}</Badge> } },
  { key: 'qty', header: 'Qty', align: 'right', className: 'font-mono text-xs text-text-muted' },
  { key: 'type', header: 'Type', className: 'font-mono text-xs text-text-muted' },
  { key: 'limit_price', header: 'Limit Price', align: 'right', className: 'font-mono text-xs text-text-muted' },
  { key: 'status', header: 'Status', render: (o) => { const v = String(o.status ?? '—'); return <Badge color={statusColor(v)}>{v}</Badge> } },
  { key: 'filled_qty', header: 'Filled Qty', align: 'right', className: 'font-mono text-xs text-text-muted' },
  { key: 'filled_avg_price', header: 'Filled Avg Price', align: 'right', className: 'font-mono text-xs text-text-muted' },
  { key: 'submitted_at', header: 'Submitted At', className: 'font-mono text-xs text-text-muted' },
]

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.orders(filter === 'all' ? undefined : filter, 30)
      setOrders(data)
    } catch { setOrders([]) }
    setLoading(false)
  }, [filter])

  useEffect(() => { refresh() }, [refresh])

  return (
    <div className="space-y-[var(--space-4)]">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Order History</h2>
          <p className="text-xs text-text-dim">{orders.length} orders</p>
        </div>
        <div className="flex items-center gap-[var(--space-3)]">
          <FilterBar options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
          <Button variant="ghost" size="sm" icon={<RefreshCw className={`w-icon-md h-icon-md ${loading ? 'animate-spin' : ''}`} />} onClick={refresh} />
        </div>
      </div>

      <Card padding="none" className="overflow-hidden">
        <DataTable<Order>
          columns={orderColumns}
          data={orders}
          emptyMessage={loading ? 'Loading orders...' : 'No orders found'}
        />
      </Card>
    </div>
  )
}

