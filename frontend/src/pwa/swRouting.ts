/**
 * Decyzja service workera, jak obsłużyć żądanie (design D2). Czysta funkcja — bez API przeglądarki,
 * żeby dało się ją testować w Vitest i współdzielić tylko z `sw.ts`.
 *
 * - `"passthrough"`: SW nie wywołuje `respondWith` — przeglądarka idzie prosto do sieci, nic nie
 *   trafia do cache. Dotyczy zawsze `/api/*` (lista, SSE czatu, logowanie), metod innych niż GET
 *   i innych domen.
 * - `"navigation"`: dokument HTML — najpierw sieć (z limitem czasu), potem powłoka z cache.
 * - `"cache-first"`: plik powłoki z listy precache bieżącej wersji.
 */
export type Route = "passthrough" | "navigation" | "cache-first";

export interface RequestInfo {
  url: string;
  method: string;
  mode: string;
}

export function isApiPath(pathname: string): boolean {
  return pathname === "/api" || pathname.startsWith("/api/");
}

export function routeRequest(
  request: RequestInfo,
  origin: string,
  precached: ReadonlySet<string>,
): Route {
  const url = new URL(request.url);
  // API jako pierwsza reguła: żadna strategia cache nie może go objąć.
  if (url.origin !== origin || request.method !== "GET" || isApiPath(url.pathname)) {
    return "passthrough";
  }
  if (request.mode === "navigate") return "navigation";
  if (precached.has(url.pathname)) return "cache-first";
  return "passthrough";
}
