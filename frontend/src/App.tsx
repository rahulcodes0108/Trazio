import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import EditTripPage from "./pages/trips/EditTripPage";
import TripDetailsPage from "./pages/trips/TripDetailsPage";
import { useRestoreSession } from "./hooks/useRestoreSession";
import { useAuthStore } from "./stores/authStore";
import DestinationsPage from "./pages/destinations/DestinationsPage";
import DestinationDetailPage from "./pages/destinations/DestinationDetailPage";

import CreateTripPage from "./pages/trips/CreateTripPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import TripsPage from "./pages/trips/TripsPage";
import ProtectedRoute from "./routes/ProtectedRoute";

function App() {
  useRestoreSession();

  const isLoading = useAuthStore(
    (state) => state.isLoading,
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
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />

        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/register"
          element={<RegisterPage />}
        />

        <Route element={<ProtectedRoute />}>
          <Route
            path="/home"
            element={<HomePage />}
          />

          <Route
            path="/trips"
            element={<TripsPage />}
          />

          <Route
            path="/trips/new"
            element={<CreateTripPage />}
          />
           <Route
            path="/trips/:tripId"
            element={<TripDetailsPage />}
          />
          <Route
            path="/trips/:tripId/edit"
            element={<EditTripPage />}
          />
          <Route
            path="/destinations"
            element={<DestinationsPage />}
          />
          <Route
            path="/destinations/:slug"
            element={<DestinationDetailPage />}
          />
        </Route>

        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;