import { Outlet } from 'react-router-dom'
import { AppSidebar } from './AppSidebar'
import { AppTopBar } from './AppTopBar'

export function AppShell() {
  return (
    <div className="min-h-screen bg-background px-4 py-6 text-foreground">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[240px_1fr]">
        <AppSidebar />
        <div className="space-y-6">
          <AppTopBar />
          <main className="rounded-lg border border-border bg-card p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
