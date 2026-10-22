/**
 * Logika banera „Dodaj do ekranu głównego” (design D5): wykrywanie platformy i trybu
 * zainstalowanego, zapamiętanie zamknięcia oraz przechwycenie `beforeinstallprompt`.
 */

/** Zdarzenie Chrome/Edge (nie ma go w typach DOM). */
export interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<unknown>;
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

export type BannerVariant = "prompt" | "ios" | null;

export const DISMISS_KEY = "kupto.installBanner.dismissedAt";
export const DISMISS_FOR_MS = 30 * 24 * 60 * 60 * 1000;

type NavigatorLike = Pick<Navigator, "userAgent" | "platform" | "maxTouchPoints"> & {
  standalone?: boolean;
};

/** iPhone/iPod/iPad, także iPadOS, który przedstawia się jako Mac z ekranem dotykowym. */
export function isIos(nav: NavigatorLike): boolean {
  if (/iPhone|iPad|iPod/i.test(nav.userAgent)) return true;
  return nav.platform === "MacIntel" && nav.maxTouchPoints > 1;
}

/** Aplikacja uruchomiona z ekranu głównego (Android/desktop: display-mode, iOS: navigator.standalone). */
export function isStandalone(win: Pick<Window, "matchMedia"> & { navigator: NavigatorLike }): boolean {
  if (win.navigator.standalone === true) return true;
  return ["standalone", "fullscreen", "minimal-ui"].some(
    (mode) => win.matchMedia?.(`(display-mode: ${mode})`).matches ?? false,
  );
}

export function isDismissed(storage: Storage | undefined, now: number): boolean {
  try {
    const raw = storage?.getItem(DISMISS_KEY);
    if (!raw) return false;
    const at = Number(raw);
    return Number.isFinite(at) && now - at < DISMISS_FOR_MS;
  } catch {
    return false; // localStorage niedostępny (np. tryb prywatny) — traktujemy jak nie zamknięty
  }
}

export function rememberDismissal(storage: Storage | undefined, now: number): void {
  try {
    storage?.setItem(DISMISS_KEY, String(now));
  } catch {
    // bez localStorage baner wróci przy następnym otwarciu — trudno
  }
}

export function bannerVariant(state: {
  standalone: boolean;
  dismissed: boolean;
  canPrompt: boolean;
  ios: boolean;
}): BannerVariant {
  if (state.standalone || state.dismissed) return null;
  if (state.canPrompt) return "prompt";
  if (state.ios) return "ios";
  return null;
}

// --- Magazyn zdarzenia `beforeinstallprompt` (może przyjść przed zamontowaniem układu) ---

let deferred: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();

function setDeferred(event: BeforeInstallPromptEvent | null) {
  deferred = event;
  listeners.forEach((listener) => listener());
}

export function getInstallPrompt(): BeforeInstallPromptEvent | null {
  return deferred;
}

export function subscribeInstallPrompt(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Zużyte zdarzenie (po `prompt()`) nie może być użyte ponownie. */
export function clearInstallPrompt(): void {
  setDeferred(null);
}

/** Wywoływane raz w `main.tsx`, zanim React cokolwiek zamontuje. */
export function captureInstallPrompt(target: Pick<Window, "addEventListener"> = window): void {
  target.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault(); // pokażemy własny baner zamiast domyślnego paska przeglądarki
    setDeferred(event as BeforeInstallPromptEvent);
  });
  target.addEventListener("appinstalled", () => setDeferred(null));
}
