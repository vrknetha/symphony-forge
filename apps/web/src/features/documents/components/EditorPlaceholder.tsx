import type { DocumentSummary } from "@/shared/types/models";

interface EditorPlaceholderProps {
  document: DocumentSummary;
}

export function EditorPlaceholder({ document }: EditorPlaceholderProps) {
  return (
    <section className="rounded-lg border border-border bg-surface p-6">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
        Proof SDK Embed
      </p>
      <h2 className="mt-3 font-display text-3xl text-surface-foreground">
        {document.title}
      </h2>
      <p className="mt-3 text-sm text-muted-foreground">
        This placeholder reserves the collaborative editor region. The main
        agent can swap in the actual Proof SDK mount or iframe once the API
        proxy and token flow are finalized.
      </p>
      <div className="mt-6 min-h-80 rounded-md border border-dashed border-border bg-background p-5 text-sm text-muted-foreground">
        <p>Proof document slug: {document.proofDocSlug}</p>
        <p className="mt-3">
          Live comments, suggestions, and multi-user editing will render here.
        </p>
      </div>
    </section>
  );
}
