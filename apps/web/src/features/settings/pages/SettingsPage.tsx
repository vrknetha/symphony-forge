import { Badge } from '@/shared/components/Badge'
import { PageHeader } from '@/shared/components/PageHeader'
import { Skeleton } from '@/shared/components/Skeleton'
import { useAgentKeys } from '../hooks/use-agent-keys'

export function SettingsPage() {
  const query = useAgentKeys()

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Settings"
        subtitle="Review agent credentials, capability scope, and recent usage without leaving the admin surface."
        title="Agent Keys"
      />
      {query.isLoading ? <Skeleton className="h-40" /> : null}
      {query.error ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          Failed to load agent keys. Check your connection and retry.
        </div>
      ) : null}
      {!query.isLoading && !query.error && (query.data?.length ?? 0) === 0 ? (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          No agent keys are configured yet.
        </div>
      ) : null}
      {!query.isLoading && !query.error && (query.data?.length ?? 0) > 0 ? (
        <div className="space-y-3">
          {query.data?.map((key) => (
            <article className="rounded-lg border border-border bg-surface p-5" key={key.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-surface-foreground">{key.name}</h2>
                <Badge tone="muted">{key.keyPrefix}</Badge>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{key.capabilities.join(' • ')}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {key.active ? 'Active' : 'Revoked'} · {key.lastUsedAt ?? 'Never used'}
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
