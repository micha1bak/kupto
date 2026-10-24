import { useEffect } from "react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { ApiError, post, setNoHouseholdHandler, setUnauthorizedHandler } from "./api/client";
import { keys, useProfile } from "./api/queries";
import { AuthForm } from "./auth/AuthForm";
import { HistoryPage } from "./history/HistoryPage";
import { HouseholdPage, HouseholdSetup } from "./household/HouseholdPage";
import { MainPage } from "./layout/MainPage";
import { ProfilePage } from "./profile/ProfilePage";
import { RecipesPage } from "./recipes/RecipesPage";
import { disablePushOnLogout } from "./pwa/push";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

function Authenticated({ page }: { page: "main" | "household" | "history" | "recipes" | "profile" }) {
  const profile = useProfile();
  const client = useQueryClient();
  const navigate = useNavigate();

  async function logout() {
    // Jeszcze z ważną sesją — serwer musi wiedzieć, czyją subskrypcję usuwa.
    await disablePushOnLogout();
    await post("/api/auth/logout");
    client.clear();
    navigate("/login");
  }

  if (profile.error instanceof ApiError && profile.error.status === 401) {
    return <Navigate to="/login" replace />;
  }
  if (!profile.data) return <p className="muted">Ładowanie…</p>;
  if (!profile.data.household) return <HouseholdSetup login={profile.data.login} />;
  if (page === "household") return <HouseholdPage />;
  if (page === "history") return <HistoryPage />;
  if (page === "recipes") return <RecipesPage />;
  if (page === "profile") return <ProfilePage profile={profile.data} onLogout={logout} />;
  return <MainPage profile={profile.data} />;
}

function Routing() {
  const navigate = useNavigate();
  const client = useQueryClient();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      client.clear();
      navigate("/login");
    });
    // Usunięty z gospodarstwa (lub gospodarstwo zniknęło): odśwież profil, by pokazać ekran
    // tworzenia/dołączania zamiast nieaktualnej listy z cache.
    setNoHouseholdHandler(() => {
      client.removeQueries({ queryKey: keys.list });
      client.removeQueries({ queryKey: keys.chat });
      client.removeQueries({ queryKey: keys.household });
      client.removeQueries({ queryKey: keys.history });
      client.removeQueries({ queryKey: keys.historySearch });
      client.removeQueries({ queryKey: keys.recipes });
      client.invalidateQueries({ queryKey: keys.profile });
    });
  }, [navigate, client]);

  return (
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route path="/household" element={<Authenticated page="household" />} />
      <Route path="/history" element={<Authenticated page="history" />} />
      <Route path="/recipes/*" element={<Authenticated page="recipes" />} />
      <Route path="/profile" element={<Authenticated page="profile" />} />
      <Route path="*" element={<Authenticated page="main" />} />
    </Routes>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routing />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
