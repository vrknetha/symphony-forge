import { useLogin } from "@/features/auth/hooks/use-login";

export function LoginPage() {
  const login = useLogin();

  return (
    <main className="min-h-screen bg-background px-6 py-10 text-foreground">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-lg border border-border bg-card/80 p-8 shadow-[0_24px_90px_-40px_rgba(38,31,25,0.5)] backdrop-blur">
          <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">
            Symphony-Forge
          </p>
          <h1 className="mt-4 max-w-xl font-display text-5xl leading-tight text-foreground">
            Collaborative project memory for plans, specs, and decisions.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-muted-foreground">
            Log in with Azure AD to manage projects, open collaborative
            documents, and hand clean context to agents without leaving the
            workspace.
          </p>
        </section>
        <section className="rounded-lg border border-border bg-surface p-8 text-surface-foreground">
          <h2 className="font-display text-3xl">Azure AD Sign-In</h2>
          <p className="mt-4 text-sm text-muted-foreground">
            The scaffold uses MSAL for redirect login and falls back to a local
            mock session until the API and Azure app registration are fully
            wired.
          </p>
          <button
            className="mt-8 w-full rounded-md bg-primary px-5 py-3 font-semibold text-primary-foreground transition hover:bg-primary/90"
            onClick={() => void login()}
            type="button"
          >
            Continue to Projects
          </button>
        </section>
      </div>
    </main>
  );
}
