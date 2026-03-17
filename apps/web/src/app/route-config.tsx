import { Navigate, type RouteObject } from 'react-router-dom'
import { AdminGuard } from '@/features/auth/components/AdminGuard'
import { AuthGuard } from '@/features/auth/components/AuthGuard'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { DocumentEditorPage } from '@/features/documents/pages/DocumentEditorPage'
import { ProjectDetailPage } from '@/features/projects/pages/ProjectDetailPage'
import { ProjectsPage } from '@/features/projects/pages/ProjectsPage'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { RouteErrorPage } from '@/shared/components/RouteErrorPage'
import { AppShell } from '@/shared/layout/AppShell'

// CONVENTION_CONFLICT: `frontend-patterns.md` prefers TanStack Router,
// but this task explicitly requires `react-router-dom` v7 routing.
export const appRoutes: RouteObject[] = [
  {
    element: <LoginPage />,
    errorElement: <RouteErrorPage />,
    path: '/login',
  },
  {
    element: <AuthGuard />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            element: <Navigate replace to="/projects" />,
            index: true,
          },
          {
            element: <ProjectsPage />,
            path: '/projects',
          },
          {
            element: <ProjectDetailPage />,
            path: '/projects/:slug',
          },
          {
            element: <DocumentEditorPage />,
            path: '/projects/:slug/docs/:docSlug',
          },
          {
            element: <AdminGuard />,
            children: [
              {
                element: <SettingsPage />,
                path: '/settings',
              },
            ],
          },
        ],
      },
    ],
  },
]
