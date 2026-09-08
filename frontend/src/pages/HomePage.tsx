import { useAuthStore } from "../stores/authStore";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <main className="app">
      <h1>Welcome to Trazio</h1>

      <p>
        Hello, {user?.full_name || user?.username || "traveler"}.
      </p>

      <button type="button" onClick={() => void logout()}>
        Sign out
      </button>
    </main>
  );
}