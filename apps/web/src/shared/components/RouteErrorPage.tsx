import { isRouteErrorResponse, useRouteError } from 'react-router-dom'
import { Button } from './Button'

export function RouteErrorPage() {
  const error = useRouteError()
  const description = isRouteErrorResponse(error)
    ? error.statusText
    : 'Something unexpected happened while loading this route.'

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md rounded-lg border border-border bg-card p-6 text-center">
        <h1 className="font-display text-3xl">Route unavailable</h1>
        <p className="mt-3 text-sm text-muted-foreground">{description}</p>
        <Button className="mt-6" onClick={() => window.history.back()} variant="secondary">
          Go back
        </Button>
      </div>
    </main>
  )
}
