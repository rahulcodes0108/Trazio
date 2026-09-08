import { useRestoreSession } from "./hooks/useRestoreSession";
import { useAuthStore } from "./stores/authStore";

function App() {
  useRestoreSession();

  const isLoading = useAuthStore((state) => state.isLoading);
  const isAuthenticated = useAuthStore(
    (state) => state.isAuthenticated,
  );

  if (isLoading) {
    return (
      <div className="app">
        <h1>Trazio</h1>
        <p>Restoring your session...</p>
      </div>
    );
  }

  return (
    <div className="app">
      <h1>Trazio</h1>
      <p>
        {isAuthenticated
          ? "Authenticated"
          : "Tourism Platform - Infrastructure Setup in Progress"}
      </p>
    </div>
  );
}

export default App;