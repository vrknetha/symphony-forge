# Frontend Patterns

React conventions optimized for agent-authored code. Enforced by linters and code review.

## Component Architecture

### File Size
- Max 100 lines per component file (stricter than backend — UI must be small)
- One component per file. No multi-component exports.
- If a component exceeds 80 lines, extract sub-components or hooks

### Composition Over Props

Components compose via children and slots, not prop explosion.

```tsx
// WRONG — prop explosion
<Card
  headerTitle="Invoice"
  headerIcon={<DollarSign />}
  headerAction={<Button>Edit</Button>}
  footerLeft={<Status />}
  footerRight={<Button>Save</Button>}
/>

// RIGHT — composition
<Card>
  <Card.Header>
    <Card.Title icon={<DollarSign />}>Invoice</Card.Title>
    <Button>Edit</Button>
  </Card.Header>
  <Card.Body>{children}</Card.Body>
  <Card.Footer>
    <Status />
    <Button>Save</Button>
  </Card.Footer>
</Card>
```

### Props Discipline
- Max 5 props before rethinking the component API
- 10+ props = the component is doing too much, split it
- Destructure props in the function signature
- Default values in destructuring, not `defaultProps`
- Use TypeScript interfaces for props, not inline types

```tsx
// Props interface — always named {Component}Props
interface InvoiceCardProps {
  invoice: Invoice;
  onEdit: (id: string) => void;
  compact?: boolean;
}

export function InvoiceCard({ invoice, onEdit, compact = false }: InvoiceCardProps) {
  // ...
}
```

### Component Naming
- PascalCase file names matching the component: `InvoiceCard.tsx`
- Co-locate related files:
  ```
  components/invoice-card/
    InvoiceCard.tsx
    InvoiceCardSkeleton.tsx
    use-invoice-card.ts
    index.ts              # Single re-export
  ```

## Custom Hooks

### When to Extract
Any logic involving state, effects, or external data → extract to a hook. Components should read like a template, not a state machine.

```tsx
// WRONG — logic in component
function InvoicePage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('date');
  // ... 40 lines of filtering, sorting, fetching logic
  return <div>...</div>;
}

// RIGHT — logic in hook
function InvoicePage() {
  const { invoices, isLoading, error, filter, setFilter, sortBy, setSortBy } = useInvoices();
  return <div>...</div>;
}
```

### Hook Rules
- Prefix with `use`: `useInvoices`, `useAuth`, `useDebounce`
- Co-locate with the component that uses them
- Shared hooks go in `src/hooks/`
- One hook per file
- Hooks can compose other hooks — prefer small hooks composed together

### useEffect Restrictions

**useEffect is NOT for data fetching.** TanStack Query handles that.

Allowed uses of useEffect:
- Subscriptions (WebSocket, EventSource, ResizeObserver)
- DOM measurement (getBoundingClientRect after render)
- Third-party library sync (chart libraries, maps, editors)
- Focus management on mount

```tsx
// WRONG
useEffect(() => {
  fetch('/api/invoices').then(r => r.json()).then(setInvoices);
}, []);

// RIGHT
const { data: invoices } = useQuery({
  queryKey: ['invoices'],
  queryFn: () => apiClient.getInvoices(),
});
```

## State Management Hierarchy

Each type of state has exactly one correct tool:

| State Type | Tool | Examples |
|-----------|------|---------|
| Server data | TanStack Query | API responses, paginated lists, cached entities |
| Global client | Zustand | Auth session, theme, sidebar open/closed |
| Local UI | useState | Modal visibility, toggle, accordion open |
| Form | react-hook-form + zod | Input values, validation, submission state |
| URL | TanStack Router | Filters, pagination, active tab |

### Rules
- **Never** fetch data in Zustand stores — that's TanStack Query's job
- **Never** use useState for server data — no manual loading/error tracking
- **Never** use React Context for frequently updating values (causes re-render cascade)
- Zustand stores are small and focused: `useAuthStore`, `useUIStore` — not `useAppStore`
- URL state is state: if a user can share the link and see the same view, it belongs in the URL

```tsx
// Zustand store — small, focused
interface AuthStore {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null }),
}));
```

## Styling (Tailwind Only)

### Zero Tolerance
- No inline styles (`style={{}}`)
- No CSS modules (`*.module.css`)
- No styled-components / emotion
- No hardcoded pixel values in className
- No color literals (`text-blue-500`) — use semantic tokens (`text-primary`)

### Design Tokens

All visual values flow through `tailwind.config.ts`:

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        primary: 'hsl(var(--primary))',
        'primary-foreground': 'hsl(var(--primary-foreground))',
        secondary: 'hsl(var(--secondary))',
        destructive: 'hsl(var(--destructive))',
        muted: 'hsl(var(--muted))',
        accent: 'hsl(var(--accent))',
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
      },
    },
  },
} satisfies Config;
```

CSS variables defined in `index.css` for light/dark theme support. Components never reference raw color values.

### Conditional Classes

Use `cn()` utility (clsx + tailwind-merge):

```tsx
import { cn } from '@/lib/utils';

function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'rounded-md px-4 py-2 font-medium transition-colors',
        variant === 'primary' && 'bg-primary text-primary-foreground hover:bg-primary/90',
        variant === 'ghost' && 'hover:bg-accent hover:text-accent-foreground',
        className,
      )}
      {...props}
    />
  );
}
```

### Responsive Design
- Mobile-first: base styles → `sm:` → `md:` → `lg:` → `xl:`
- Use Tailwind breakpoints, never custom media queries
- Test at 375px (mobile), 768px (tablet), 1280px (desktop)

## Error & Loading States

Every async component handles three states. No exceptions.

### Required States
```tsx
function InvoiceList() {
  const { data, isLoading, error } = useInvoices();

  if (isLoading) return <InvoiceListSkeleton />;     // Skeleton, not spinner
  if (error) return <ErrorCard error={error} />;      // Actionable error
  if (!data?.length) return <EmptyState />;            // Empty state
  return <ul>{data.map(i => <InvoiceRow key={i.id} invoice={i} />)}</ul>;
}
```

### Rules
- **Skeleton loaders** over spinners (agents default to spinners — override this)
- **Error boundaries** per route, not just one global boundary
- **Suspense boundaries** for lazy-loaded routes
- **Empty states** are designed, not afterthoughts ("No invoices yet" with a CTA)
- Error messages suggest next action: "Failed to load invoices. Check your connection and retry."

### Error Boundary Pattern
```tsx
// Per-route error boundary
<Route
  path="/invoices"
  component={InvoicesPage}
  errorComponent={({ error }) => (
    <ErrorCard
      error={error}
      action={{ label: 'Go back', onClick: () => router.navigate({ to: '/' }) }}
    />
  )}
/>
```

## Accessibility (Non-Negotiable)

Agents always skip this. These rules are enforced by eslint-plugin-jsx-a11y:

| Rule | Enforcement |
|------|------------|
| Interactive elements keyboard-navigable | Lint error |
| All `<img>` have `alt` text | Lint error |
| Form inputs have associated `<label>` | Lint error |
| Custom widgets have ARIA attributes | Lint error |
| Color contrast meets WCAG AA (4.5:1) | Design review |
| Focus visible on all interactive elements | Tailwind `focus-visible:` ring |
| No `onClick` on non-interactive elements | Lint error — use `<button>` |

shadcn/ui components are accessible by default. Don't override their ARIA attributes.

## Data Fetching (TanStack Query Only)

```tsx
// Query keys — structured and consistent
export const invoiceKeys = {
  all: ['invoices'] as const,
  lists: () => [...invoiceKeys.all, 'list'] as const,
  list: (filters: InvoiceFilters) => [...invoiceKeys.lists(), filters] as const,
  details: () => [...invoiceKeys.all, 'detail'] as const,
  detail: (id: string) => [...invoiceKeys.details(), id] as const,
};

// Query hook
export function useInvoice(id: string) {
  return useQuery({
    queryKey: invoiceKeys.detail(id),
    queryFn: () => apiClient.getInvoice(id),
    staleTime: 5 * 60 * 1000,
  });
}

// Mutation hook
export function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: apiClient.createInvoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() });
    },
  });
}
```

### Rules
- Structured query key factories (never ad-hoc string keys)
- Mutations invalidate related queries
- `staleTime` set explicitly per query (no global default — each query knows its freshness needs)
- Loading/error states handled at the component level, not in the hook
- API client is orval-generated from OpenAPI spec — no manual fetch wrappers

## File Organization

```
src/
  routes/                     # TanStack Router pages
    __root.tsx                # Root layout
    index.tsx                 # Dashboard
    invoices/
      index.tsx               # List page
      $invoiceId.tsx          # Detail page
  components/
    ui/                       # shadcn/ui primitives (button, input, dialog)
    layout/                   # Shell, sidebar, nav, footer
    shared/                   # App-wide reusable (ErrorCard, EmptyState, Skeleton)
    invoices/                 # Domain-specific components
      InvoiceCard.tsx
      InvoiceTable.tsx
      InvoiceForm.tsx
  hooks/                      # Shared hooks
    use-debounce.ts
    use-media-query.ts
  stores/                     # Zustand stores
    auth-store.ts
    ui-store.ts
  lib/                        # Utilities
    api-client.ts             # orval-generated
    query-client.ts
    utils.ts                  # cn() helper
  types/                      # Frontend-specific types
```

### Rules
- Routes are thin — data fetching in hooks, UI in components
- `components/ui/` is shadcn/ui managed — don't manually edit
- Domain components (`components/invoices/`) co-locate with their hooks
- No `utils/helpers.ts` catch-all — name files by what they do

## Anti-Patterns (Agents Do These — Block Them)

| Anti-Pattern | Fix |
|-------------|-----|
| God component (300+ lines) | Split into composition + hooks |
| Prop drilling 4+ levels | Use composition, context, or Zustand |
| `any` in props/state | Typed interfaces always |
| Fetching in useEffect | TanStack Query |
| Global spinner component | Skeleton loaders per component |
| `onClick` on `<div>` | Use `<button>` — it's accessible |
| Hardcoded strings in UI | i18n-ready: extract to constants minimum |
| Index files that re-export everything | One level of re-export only |
| CSS-in-JS or inline styles | Tailwind + cn() |
| `text-blue-500` everywhere | Semantic tokens: `text-primary` |
