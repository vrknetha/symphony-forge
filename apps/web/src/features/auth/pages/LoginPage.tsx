import { Navigate, useLocation } from 'react-router-dom'
import { appEnv } from '@/config/env'
import { Button } from '@/shared/components/Button'
import { useAuth } from '../hooks/use-auth'

export function LoginPage() {
  const location = useLocation()
  const { isAuthenticated, login } = useAuth()
  const nextPath = (location.state as { from?: string } | null)?.from ?? '/projects'

  if (isAuthenticated) {
    return <Navigate replace to={nextPath} />
  }

  return (
    <main className="min-h-screen bg-background px-6 py-10 text-foreground">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-lg border border-border bg-card p-8 shadow-sm">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">
            Symphony-Forge
          </p>
          <h1 className="mt-4 max-w-xl font-display text-5xl leading-tight">
            Collaborative project memory for plans, specs, and decisions.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-muted-foreground">
            Log in with Azure AD to manage projects, open collaborative documents, and keep
            shared engineering context ready for the next agent handoff.
          </p>
        </section>
        <section className="rounded-lg border border-border bg-surface p-8 text-surface-foreground">
          <h2 className="font-display text-3xl">Azure AD Sign-In</h2>
          <p className="mt-4 text-sm text-muted-foreground">
            The dashboard uses MSAL redirect auth. Local mock mode stays available until
            the API and Azure app registration are fully wired.
          </p>
          <p className="mt-4 rounded-md bg-card px-3 py-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {appEnv.useMocks ? 'Local mock session enabled' : 'Azure redirect flow enabled'}
          </p>
          <Button className="mt-8 w-full" onClick={() => void login()}>
            Continue to Projects
          </Button>
        </section>
      </div>
    </main>
  )
}
