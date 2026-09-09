import type { ReactNode } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

interface ProtectedRouteProps {
  children?: ReactNode;
}

export default function ProtectedRoute({
  children,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthStore();

  console.log("PROTECTED ROUTE:", {
    isAuthenticated,
    isLoading,
    path: window.location.pathname,
  });
  if (isLoading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner" />
        <p>Restoring your session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}