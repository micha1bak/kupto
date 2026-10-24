import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { keys } from "../api/queries";
import type { Profile } from "../api/types";

export const MAX_EMAIL_LENGTH = 254;

/** Wstępna kontrola w przeglądarce; pełną walidację (i link weryfikacyjny) robi serwer. */
export function validateEmail(email: string): string | null {
  const trimmed = email.trim();
  if (!trimmed) return "Podaj adres e-mail.";
  if (trimmed.length > MAX_EMAIL_LENGTH || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed)) {
    return "Podaj poprawny adres e-mail.";
  }
  return null;
}

export function errorText(error: unknown): string | null {
  if (!error) return null;
  return error instanceof ApiError ? error.message : "Brak połączenia z serwerem.";
}

/** Termin potwierdzenia adresu w czytelnej postaci, np. „31 października”. */
export function formatDeadline(iso: string): string {
  return new Date(iso).toLocaleDateString("pl-PL", { day: "numeric", month: "long" });
}

/**
 * Wysłanie linku weryfikacyjnego (`POST /api/users/me/email`): podanie adresu, zmiana
 * niepotwierdzonego adresu albo ponowne wysłanie na ten sam. Profil w cache od razu się zmienia.
 */
export function useSendVerification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (email: string) => post<Profile>("/api/users/me/email", { email: email.trim() }),
    onSuccess: (profile) => queryClient.setQueryData(keys.profile, profile),
  });
}
