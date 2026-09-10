import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { useRestoreSession } from "./hooks/useRestoreSession";

import ProtectedRoute from "./routes/ProtectedRoute";

import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import HomePage from "./pages/HomePage";

import TripsPage from "./pages/trips/TripsPage";
import CreateTripPage from "./pages/trips/CreateTripPage";
import TripDetailsPage from "./pages/trips/TripDetailsPage";
import EditTripPage from "./pages/trips/EditTripPage";

import DestinationsPage from "./pages/destinations/DestinationsPage";
import DestinationDetailPage from "./pages/destinations/DestinationDetailPage";

import ItineraryPage from "./pages/itineraries/ItineraryPage";
import ActiveTripPage from "./pages/trips/ActiveTripPage";

function App() {
  useRestoreSession();

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}

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

        {/* Protected routes */}

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
            path="/trips/:tripId/itineraries/:itineraryId"
            element={<ItineraryPage />}
          />

          <Route
            path="/trips/:tripId/itineraries/:itineraryId/active"
            element={<ActiveTripPage />}
          />

          <Route
            path="/destinations/:slug"
            element={<DestinationDetailPage />}
          />

          <Route
            path="/trips/:tripId/itineraries/:itineraryId"
            element={<ItineraryPage />}
          />
        </Route>

        {/* Unknown routes */}

        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;