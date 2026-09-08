import { useEffect } from "react";

import { useAuthStore } from "../stores/authStore";

export function useRestoreSession(): void {
  const restoreSession = useAuthStore(
    (state) => state.restoreSession,
  );

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);
}