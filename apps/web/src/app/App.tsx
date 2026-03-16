import { useAuthBootstrap } from "@/features/auth/hooks/use-auth-bootstrap";
import { AppRouter } from "./router";

export function App() {
  useAuthBootstrap();
  return <AppRouter />;
}
