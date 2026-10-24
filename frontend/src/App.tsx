import { useEffect } from "react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import {
  ApiError,
  post,
  setEmailBlockedHandler,
  setNoHouseholdHandler,
  setUnauthorizedHandler,
} from "./api/client";
import { keys, useProfile } from "./api/queries";
import { EmailGate } from "./account/EmailGate";
import { AuthForm } from "./auth/AuthForm";
import { ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from "./auth/TokenPages";
import { ChatArchivePage } from "./chat/ChatArchivePage";
import { HistoryPage } from "./history/HistoryPage";
import { HouseholdPage, HouseholdSetup } from "./household/HouseholdPage";
import { MainPage } from "./layout/MainPage";
import { MealPlanPage } from "./mealPlan/MealPlanPage";
import { NameSetup } from "./profile/NameSetup";
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

type Page =
  | "main"
  | "household"
  | "history"
  | "recipes"
  | "meal-plan"
  | "profile"
  | "chat-archive";

function Authenticated({ page }: { page: Page }) {
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
  // Konto sprzed czatu grupowego (#78) najpierw uzupełnia imię — reszta aplikacji czeka.
  if (!profile.data.name) return <NameSetup onLogout={logout} />;
  // Adres e-mail (#77): podanie (stare konto) albo potwierdzenie po terminie — reszta czeka.
  if (profile.data.email_blocked) return <EmailGate profile={profile.data} onLogout={logout} />;
  if (!profile.data.household) return <HouseholdSetup profile={profile.data} />;
  if (page === "household") return <HouseholdPage />;
  if (page === "history") return <HistoryPage />;
  if (page === "recipes") return <RecipesPage />;
  if (page === "meal-plan") return <MealPlanPage />;
  if (page === "chat-archive") return <ChatArchivePage />;
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
      client.removeQueries({ queryKey: keys.mealPlan });
      client.invalidateQueries({ queryKey: keys.profile });
    });
    // Termin potwierdzenia adresu minął w trakcie pracy — profil pokaże ekran blokady.
    setEmailBlockedHandler(() => client.invalidateQueries({ queryKey: keys.profile }));
  }, [navigate, client]);

  return (
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/household" element={<Authenticated page="household" />} />
      <Route path="/history" element={<Authenticated page="history" />} />
      <Route path="/recipes/*" element={<Authenticated page="recipes" />} />
      <Route path="/meal-plan" element={<Authenticated page="meal-plan" />} />
      <Route path="/profile" element={<Authenticated page="profile" />} />
      <Route path="/chat-archive" element={<Authenticated page="chat-archive" />} />
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
