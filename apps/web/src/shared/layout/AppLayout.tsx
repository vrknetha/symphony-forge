import { NavLink, Outlet } from "react-router-dom";
import { useAuthStore } from "@/features/auth/store/use-auth-store";
import { cn } from "@/shared/lib/cn";

const navItems = [
  { label: "Projects", to: "/projects" },
  { label: "Settings", to: "/settings" },
];

export function AppLayout() {
  const { clearUser, user } = useAuthStore();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[240px_1fr]">
        <aside className="rounded-lg border border-border bg-card p-5">
          <div className="border-b border-border pb-5">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Workspace
            </p>
            <h1 className="mt-2 font-display text-3xl">Symphony-Forge</h1>
          </div>
          <nav className="mt-5 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                className={({ isActive }) =>
                  cn(
                    "block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition",
                    isActive && "bg-primary text-primary-foreground",
                  )
                }
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-8 rounded-md bg-surface p-4 text-sm">
            <p className="font-semibold text-surface-foreground">
              {user?.name}
            </p>
            <p className="text-muted-foreground">{user?.email}</p>
            <button
              className="mt-4 rounded-md border border-border px-3 py-2 text-sm text-foreground transition hover:bg-background"
              onClick={clearUser}
              type="button"
            >
              Sign out
            </button>
          </div>
        </aside>
        <main className="rounded-lg border border-border bg-card p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
