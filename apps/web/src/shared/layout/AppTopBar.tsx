import { useLocation } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/use-auth'
import { Badge } from '@/shared/components/Badge'
import { Button } from '@/shared/components/Button'

function getSectionLabel(pathname: string) {
  if (pathname.startsWith('/settings')) {
    return 'Settings'
  }

  if (pathname.startsWith('/projects/')) {
    return 'Project workspace'
  }

  return 'Projects'
}

export function AppTopBar() {
  const location = useLocation()
  const { logout, user } = useAuth()

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card p-4">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          {getSectionLabel(location.pathname)}
        </p>
        <h2 className="mt-1 text-lg font-semibold">{user?.name}</h2>
      </div>
      <div className="flex items-center gap-3">
        <Badge tone="muted">{user?.role ?? 'MEMBER'}</Badge>
        <span className="text-sm text-muted-foreground">{user?.email}</span>
        <Button onClick={() => void logout()} variant="ghost">
          Sign out
        </Button>
      </div>
    </header>
  )
}
