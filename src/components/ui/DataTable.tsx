import type { ReactNode } from 'react'

/* ─── DataTable ────────────────────────────────────────────────
   Pencil.dev design-token-driven data table with typed columns.
   Tokens: --color-border, --color-bg-hover, --color-text-dim,
           --space-3, --space-4, --text-xs, --text-sm
   ────────────────────────────────────────────────────────────── */

export interface Column<T> {
  key: string
  header: string
  align?: 'left' | 'right' | 'center'
  render?: (row: T, index: number) => ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  emptyMessage?: string
  footer?: ReactNode
  onRowClick?: (row: T, index: number) => void
}

export default function DataTable<T>({ columns, data, emptyMessage = 'No data', footer, onRowClick }: DataTableProps<T>) {
  if (data.length === 0) {
    return <div className="text-center py-[var(--space-8)] text-text-dim text-sm">{emptyMessage}</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            {columns.map(col => (
              <th
                key={col.key}
                className={`py-[var(--space-3)] px-[var(--space-4)] text-xs text-text-dim uppercase tracking-wider font-medium ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              className={`border-b border-border/50 hover:bg-bg-hover transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              onClick={() => onRowClick?.(row, i)}
            >
              {columns.map(col => (
                <td
                  key={col.key}
                  className={`py-[var(--space-3)] px-[var(--space-4)] ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'} ${col.className ?? ''}`}
                >
                  {col.render ? col.render(row, i) : String((row as Record<string, unknown>)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {footer && <tfoot>{footer}</tfoot>}
      </table>
    </div>
  )
}

