/**
 * Rejestracja service workera i dostarczanie nowych wersji (design D3).
 *
 * - Przeglądarka sprawdza `/sw.js` przy każdej nawigacji; dodatkowo sprawdzamy przy powrocie
 *   strony na pierwszy plan, bo zainstalowana aplikacja wznowiona z tła nie nawiguje.
 * - Nowy SW przejmuje stronę od razu (`skipWaiting` + `clients.claim`). Jeśli strona była już
 *   kontrolowana (czyli to aktualizacja, a nie pierwsza instalacja), przeładowujemy ją przy
 *   najbliższym przejściu w tło — użytkownik po powrocie ma nową wersję, a nic nie miga mu
 *   przed oczami.
 */

export interface RegisterDeps {
  serviceWorker?: ServiceWorkerContainer;
  document: Pick<Document, "visibilityState" | "addEventListener">;
  reload: () => void;
}

export const SW_URL = "/sw.js";

export async function registerServiceWorker(
  deps: RegisterDeps = {
    serviceWorker: "serviceWorker" in navigator ? navigator.serviceWorker : undefined,
    document,
    reload: () => window.location.reload(),
  },
): Promise<ServiceWorkerRegistration | undefined> {
  const { serviceWorker, document: doc, reload } = deps;
  if (!serviceWorker) return undefined;

  let controlled = serviceWorker.controller !== null;
  let reloadPending = false;

  serviceWorker.addEventListener("controllerchange", () => {
    if (!controlled) {
      controlled = true; // pierwsza instalacja — strona już działa na bieżącej wersji
      return;
    }
    if (doc.visibilityState === "hidden") reload();
    else reloadPending = true;
  });

  const registration = await serviceWorker.register(SW_URL, {
    scope: "/",
    updateViaCache: "none",
  });

  doc.addEventListener("visibilitychange", () => {
    if (doc.visibilityState === "hidden") {
      if (reloadPending) {
        reloadPending = false;
        reload();
      }
    } else {
      registration.update().catch(() => {
        // brak sieci — sprawdzimy przy następnym powrocie
      });
    }
  });

  return registration;
}
