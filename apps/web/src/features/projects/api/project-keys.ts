export const projectKeys = {
  all: ['projects'] as const,
  detail: (slug: string) => [...projectKeys.all, 'detail', slug] as const,
  list: () => [...projectKeys.all, 'list'] as const,
}
