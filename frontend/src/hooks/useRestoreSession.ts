import { useEffect, useRef } from "react";

import { useAuthStore } from "../stores/authStore";

export function useRestoreSession(): void {
  const restoreSession = useAuthStore(
    (state) => state.restoreSession,
  );

  const hasRestored = useRef(false);

  useEffect(() => {
    if (hasRestored.current) {
      return;
    }

    hasRestored.current = true;

    void restoreSession();
  }, [restoreSession]);
}