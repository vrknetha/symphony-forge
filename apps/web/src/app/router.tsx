import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/shared/layout/AppLayout";
import { AuthGuard } from "@/features/auth/components/AuthGuard";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { DocumentEditorPage } from "@/features/documents/pages/DocumentEditorPage";
import { ProjectDetailPage } from "@/features/projects/pages/ProjectDetailPage";
import { ProjectsPage } from "@/features/projects/pages/ProjectsPage";
import { SettingsPage } from "@/features/settings/pages/SettingsPage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route element={<AuthGuard />}>
          <Route element={<AppLayout />}>
            <Route element={<Navigate replace to="/projects" />} path="/" />
            <Route element={<ProjectsPage />} path="/projects" />
            <Route element={<ProjectDetailPage />} path="/projects/:slug" />
            <Route
              element={<DocumentEditorPage />}
              path="/projects/:slug/docs/:docSlug"
            />
            <Route element={<SettingsPage />} path="/settings" />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
