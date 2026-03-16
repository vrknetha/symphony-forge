import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/use-auth-store";

export function AuthGuard() {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }

  return <Outlet />;
}
