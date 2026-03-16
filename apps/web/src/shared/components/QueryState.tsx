import type { ReactNode } from "react";

interface QueryStateProps {
  children: ReactNode;
  emptyMessage: string;
  error?: Error | null;
  isEmpty?: boolean;
  isLoading: boolean;
}

export function QueryState({
  children,
  emptyMessage,
  error,
  isEmpty = false,
  isLoading,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
        Loading data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
        Failed to load data. Check your connection and retry.
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return children;
}
