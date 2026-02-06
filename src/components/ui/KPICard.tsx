import type { ElementType } from 'react'

/* ─── KPICard ──────────────────────────────────────────────────
   Pencil.dev design-token-driven metric card for dashboards.
   Tokens: --color-bg-card, --color-border, --radius-xl,
           --space-*, --text-xs, --icon-md, --icon-box-md
   ────────────────────────────────────────────────────────────── */

interface KPICardProps {
  label: string
  value: string
  icon: ElementType
  color: string   // Tailwind text color class, e.g. 'text-accent-blue'
  bg: string      // Tailwind bg class, e.g. 'bg-accent-blue/10'
}

export default function KPICard({ label, value, icon: Icon, color, bg }: KPICardProps) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-[var(--space-4)] shadow-sm hover:border-border-light hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-[var(--space-3)]">
        <span className="text-xs text-text-dim uppercase tracking-wider font-medium">{label}</span>
        <div className={`w-icon-box-md h-icon-box-md rounded-lg ${bg} flex items-center justify-center`}>
          <Icon className={`w-icon-md h-icon-md ${color}`} />
        </div>
      </div>
      <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
    </div>
  )
}

