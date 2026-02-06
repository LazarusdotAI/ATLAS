import { type Position } from '../../api'
import { Card, CardHeader, CardTitle, Badge, DataTable, type Column } from '../ui'

const cols: Column<Position>[] = [
  { key: 'symbol', header: 'Symbol', render: p => <span className="font-semibold">{p.symbol}</span> },
  { key: 'qty', header: 'Qty', align: 'right', render: p => (
    <span className="font-mono text-xs">{p.qty} <span className="text-text-dim">{p.side}</span></span>
  )},
  { key: 'entry_price', header: 'Entry', align: 'right', render: p => (
    <span className="font-mono text-xs">${p.entry_price.toFixed(2)}</span>
  )},
  { key: 'current_price', header: 'Price', align: 'right', render: p => (
    <span className="font-mono text-xs">${p.current_price.toFixed(2)}</span>
  )},
  { key: 'unrealised_pnl', header: 'P&L', align: 'right', render: p => (
    <span className={`font-mono text-xs font-semibold ${p.unrealised_pnl >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
      {p.unrealised_pnl >= 0 ? '+' : ''}${p.unrealised_pnl.toFixed(2)}
    </span>
  )},
]

interface Props { positions: Position[] }

export default function PositionsPanel({ positions }: Props) {
  const total = positions.reduce((s, p) => s + p.unrealised_pnl, 0)
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="px-[var(--space-4)] pt-[var(--space-4)]">
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <Badge color={positions.length > 0 ? (total >= 0 ? 'green' : 'red') : 'dim'}>
            {positions.length} open
          </Badge>
        </CardHeader>
      </div>
      <DataTable<Position>
        columns={cols}
        data={positions}
        emptyMessage="No open positions"
        footer={positions.length > 0 ? (
          <tr className="text-text-muted font-semibold text-xs">
            <td className="pt-[var(--space-3)] px-[var(--space-4)]" colSpan={4}>Total Unrealised</td>
            <td className={`pt-[var(--space-3)] px-[var(--space-4)] text-right font-mono ${total >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
              {total >= 0 ? '+' : ''}${total.toFixed(2)}
            </td>
          </tr>
        ) : undefined}
      />
    </Card>
  )
}

