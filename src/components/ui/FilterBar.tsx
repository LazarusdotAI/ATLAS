/* ─── FilterBar ────────────────────────────────────────────────
   Pencil.dev design-token-driven segmented filter / tab bar.
   Tokens: --color-bg-card, --color-border, --color-accent-green,
           --radius-lg, --radius-md, --space-*, --text-xs
   ────────────────────────────────────────────────────────────── */

interface FilterBarProps {
  options: { id: string; label: string }[]
  value: string
  onChange: (id: string) => void
}

export default function FilterBar({ options, value, onChange }: FilterBarProps) {
  return (
    <div className="flex items-center gap-[var(--space-1)] bg-bg-card border border-border rounded-lg p-[var(--space-1)]">
      {options.map(opt => (
        <button
          key={opt.id}
          onClick={() => onChange(opt.id)}
          className={`px-[var(--space-3)] py-[var(--space-1-5)] rounded-md text-xs font-medium transition-all capitalize
            ${value === opt.id ? 'bg-accent-green/10 text-accent-green' : 'text-text-dim hover:text-text-muted'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

