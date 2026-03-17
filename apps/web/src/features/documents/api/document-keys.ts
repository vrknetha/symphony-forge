export const documentKeys = {
  detail: (projectSlug: string, docSlug: string) =>
    ['projects', projectSlug, 'documents', 'detail', docSlug] as const,
  list: (projectSlug: string) => ['projects', projectSlug, 'documents', 'list'] as const,
}
