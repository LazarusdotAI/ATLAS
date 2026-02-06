/* ─── LoadingFallback ──────────────────────────────────────────
   Pencil.dev design-token-driven loading spinner.
   Tokens: --icon-box-md, --color-accent-blue, --space-3, --text-sm
   ────────────────────────────────────────────────────────────── */

export default function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full min-h-[60vh]">
      <div className="flex flex-col items-center gap-[var(--space-3)]">
        <div className="w-icon-box-md h-icon-box-md border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
        <span className="text-sm text-text-muted">Loading…</span>
      </div>
    </div>
  )
}

