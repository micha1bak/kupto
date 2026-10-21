import { useEffect } from "react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { ApiError, post, setUnauthorizedHandler } from "./api/client";
import { useProfile } from "./api/queries";
import { AuthForm } from "./auth/AuthForm";
import { HouseholdPage, HouseholdSetup } from "./household/HouseholdPage";
import { MainPage } from "./layout/MainPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

function Authenticated({ page }: { page: "main" | "household" }) {
  const profile = useProfile();
  const client = useQueryClient();
  const navigate = useNavigate();

  async function logout() {
    await post("/api/auth/logout");
    client.clear();
    navigate("/login");
  }

  if (profile.error instanceof ApiError && profile.error.status === 401) {
    return <Navigate to="/login" replace />;
  }
  if (!profile.data) return <p className="muted">Ładowanie…</p>;
  if (!profile.data.household) return <HouseholdSetup login={profile.data.login} />;
  return page === "household" ? (
    <HouseholdPage />
  ) : (
    <MainPage profile={profile.data} onLogout={logout} />
  );
}

function Routing() {
  const navigate = useNavigate();
  const client = useQueryClient();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      client.clear();
      navigate("/login");
    });
  }, [navigate, client]);

  return (
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route path="/household" element={<Authenticated page="household" />} />
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
