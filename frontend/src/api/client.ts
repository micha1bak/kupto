export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code: string | null = null,
  ) {
    super(message);
  }
}

/** Kod błędu backendu: użytkownik nie należy (już) do żadnego gospodarstwa. */
export const NO_HOUSEHOLD = "no_household";

let onUnauthorized: () => void = () => {};
let onNoHousehold: () => void = () => {};

/** Rejestruje reakcję na wygaśnięcie sesji (np. przejście do ekranu logowania). */
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

/** Rejestruje reakcję na utratę gospodarstwa (np. usunięcie przez właściciela). */
export function setNoHouseholdHandler(handler: () => void) {
  onNoHousehold = handler;
}

export async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = "Coś poszło nie tak. Spróbuj ponownie.";
  let code: string | null = null;
  try {
    const body = await response.json();
    if (typeof body.code === "string") code = body.code;
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = "Sprawdź poprawność wprowadzonych danych.";
  } catch {
    // brak treści JSON — zostaje komunikat domyślny
  }
  return new ApiError(response.status, message, code);
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (response.status === 401 && !path.startsWith("/api/auth/")) onUnauthorized();
  if (!response.ok) {
    const error = await errorFromResponse(response);
    if (error.code === NO_HOUSEHOLD) onNoHousehold();
    throw error;
  }
  return response;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init);
  return response.status === 204 ? (undefined as T) : response.json();
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });
