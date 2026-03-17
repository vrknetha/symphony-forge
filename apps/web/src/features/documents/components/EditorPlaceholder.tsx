import { Badge } from '@/shared/components/Badge'
import { Button } from '@/shared/components/Button'
import type { DocumentDetail } from '@/shared/types/models'

interface EditorPlaceholderProps {
  document: DocumentDetail
  isSidebarOpen: boolean
  onToggleSidebar: () => void
}

export function EditorPlaceholder({
  document,
  isSidebarOpen,
  onToggleSidebar,
}: EditorPlaceholderProps) {
  return (
    <section className="grid gap-6 xl:grid-cols-[1fr_280px]">
      <div className="rounded-lg border border-border bg-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Proof SDK Embed</p>
            <h2 className="mt-2 font-display text-3xl text-surface-foreground">{document.title}</h2>
          </div>
          <Badge>{document.docType}</Badge>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          This region is ready for the collaborative Proof editor mount once the proxy
          token flow is finalized.
        </p>
        <div className="mt-6 min-h-96 rounded-md border border-dashed border-border bg-background p-5 text-sm text-muted-foreground">
          <p>Proof document slug: {document.proofDocSlug}</p>
          <p className="mt-3">Real-time comments, suggestions, and multi-user editing will render here.</p>
        </div>
      </div>
      <aside className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">Document sidebar</h3>
          <Button onClick={onToggleSidebar} variant="ghost">
            {isSidebarOpen ? 'Collapse' : 'Expand'}
          </Button>
        </div>
        {isSidebarOpen ? (
          <div className="mt-4 space-y-4 text-sm text-muted-foreground">
            <div>
              <p className="font-medium text-foreground">Status</p>
              <p>{document.versionLabel}</p>
            </div>
            <div>
              <p className="font-medium text-foreground">Proof route</p>
              <p>{document.proofUrl}</p>
            </div>
            <div>
              <p className="font-medium text-foreground">Version history</p>
              <p>Recent updates will appear here once the editor integration is live.</p>
            </div>
          </div>
        ) : null}
      </aside>
    </section>
  )
}
