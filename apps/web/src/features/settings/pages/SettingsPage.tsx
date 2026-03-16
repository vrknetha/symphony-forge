import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/shared/components/PageHeader";
import { QueryState } from "@/shared/components/QueryState";
import { listAgentKeys } from "../api/settings-api";

export function SettingsPage() {
  const query = useQuery({ queryFn: listAgentKeys, queryKey: ["agent-keys"] });

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Settings"
        subtitle="Review agent credentials, capability scope, and recent usage without leaving the admin surface."
        title="Agent Keys"
      />
      <QueryState
        emptyMessage="No agent keys are configured."
        error={query.error}
        isEmpty={(query.data?.length ?? 0) === 0}
        isLoading={query.isLoading}
      >
        <div className="space-y-3">
          {query.data?.map((key) => (
            <article
              className="rounded-lg border border-border bg-surface p-5"
              key={key.id}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-surface-foreground">
                  {key.name}
                </h2>
                <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  {key.keyPrefix}
                </span>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {key.capabilities.join(" • ")}
              </p>
            </article>
          ))}
        </div>
      </QueryState>
    </section>
  );
}
