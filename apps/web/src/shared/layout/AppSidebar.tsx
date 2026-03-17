import { NavLink } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/use-auth'
import { cn } from '@/shared/lib/cn'

export function AppSidebar() {
  const { isAdmin } = useAuth()
  const links = [
    { label: 'Projects', to: '/projects' },
    ...(isAdmin ? [{ label: 'Settings', to: '/settings' }] : []),
  ]

  return (
    <aside className="rounded-lg border border-border bg-card p-5">
      <div className="border-b border-border pb-5">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Workspace</p>
        <h1 className="mt-2 font-display text-3xl">Symphony-Forge</h1>
      </div>
      <nav className="mt-5 space-y-2">
        {links.map((link) => (
          <NavLink
            className={({ isActive }) =>
              cn(
                'block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition',
                isActive && 'bg-primary text-primary-foreground',
              )
            }
            key={link.to}
            to={link.to}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
