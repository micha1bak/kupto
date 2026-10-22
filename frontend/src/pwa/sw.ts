/**
 * Service worker Kupto (design D1–D4). Budowany przez `swPlugin.ts` do `dist/sw.js`; wtyczka
 * podmienia znaczniki `__KUPTO_PRECACHE__` i `__KUPTO_SW_VERSION__` na listę plików powłoki
 * i wersję buildu. Plik nie może importować modułów współdzielonych z aplikacją (inaczej bundler
 * wydzieliłby wspólny kawałek, a SW musi być jednym plikiem).
 */
import { routeRequest } from "./swRouting";
import { parsePushPayload, pickWindow, resolveClickUrl } from "./swNotifications";

declare const __KUPTO_PRECACHE__: string[];
declare const __KUPTO_SW_VERSION__: string;

// Minimalne typy API service workera — biblioteka TS „WebWorker” koliduje z „DOM” w jednym projekcie.
interface ExtendableEvent extends Event {
  waitUntil(promise: Promise<unknown>): void;
}
interface FetchEvent extends ExtendableEvent {
  readonly request: Request;
  respondWith(response: Response | Promise<Response>): void;
}
interface PushEvent extends ExtendableEvent {
  readonly data: { text(): string } | null;
}
interface NotificationEvent extends ExtendableEvent {
  readonly notification: Notification;
}
interface WindowClient {
  readonly url: string;
  focus(): Promise<WindowClient>;
}
interface ServiceWorkerScope {
  readonly location: Location;
  readonly registration: ServiceWorkerRegistration;
  skipWaiting(): Promise<void>;
  readonly clients: {
    claim(): Promise<void>;
    matchAll(options: { type: "window"; includeUncontrolled: boolean }): Promise<WindowClient[]>;
    openWindow(url: string): Promise<WindowClient | null>;
  };
  addEventListener(type: "install" | "activate", listener: (event: ExtendableEvent) => void): void;
  addEventListener(type: "fetch", listener: (event: FetchEvent) => void): void;
  addEventListener(type: "push", listener: (event: PushEvent) => void): void;
  addEventListener(type: "notificationclick", listener: (event: NotificationEvent) => void): void;
}

const sw = self as unknown as ServiceWorkerScope;

const CACHE_PREFIX = "kupto-shell-";
const CACHE_NAME = `${CACHE_PREFIX}${__KUPTO_SW_VERSION__}`;
const PRECACHE = new Set(__KUPTO_PRECACHE__);
/** Po tylu ms bez odpowiedzi sieci nawigacja dostaje powłokę z cache (słaby zasięg w sklepie). */
const NAVIGATION_TIMEOUT_MS = 3000;

// --- Cykl życia: cała powłoka bieżącej wersji w jednym cache, stare wersje usuwane ---

sw.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      // `reload` omija cache HTTP, żeby nie zapisać nieaktualnego index.html.
      await cache.addAll([...PRECACHE].map((url) => new Request(url, { cache: "reload" })));
      await sw.skipWaiting();
    })(),
  );
});

sw.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
          .map((name) => caches.delete(name)),
      );
      await sw.clients.claim();
    })(),
  );
});

// --- Żądania: /api/* i wszystko spoza powłoki idzie do sieci bez udziału SW ---

sw.addEventListener("fetch", (event) => {
  const route = routeRequest(event.request, sw.location.origin, PRECACHE);
  if (route === "navigation") event.respondWith(navigation(event.request));
  else if (route === "cache-first") event.respondWith(cacheFirst(event.request));
  // "passthrough": brak respondWith — przeglądarka obsługuje żądanie sama (SSE, ciasteczka bez zmian).
});

async function navigation(request: Request): Promise<Response> {
  const network = fetch(request);
  const timeout = new Promise<undefined>((resolve) =>
    setTimeout(resolve, NAVIGATION_TIMEOUT_MS, undefined),
  );
  try {
    const response = await Promise.race([network, timeout]);
    if (response) return response;
  } catch {
    // brak sieci — powłoka z cache poniżej
  }
  const cached = await caches.match("/", { cacheName: CACHE_NAME });
  // Bez powłoki w cache (np. w trakcie pierwszej instalacji) czekamy na sieć mimo limitu.
  return cached ?? network;
}

async function cacheFirst(request: Request): Promise<Response> {
  const cached = await caches.match(request, { cacheName: CACHE_NAME });
  return cached ?? fetch(request);
}

// --- Powiadomienia push (#27, design D8) ---

sw.addEventListener("push", (event) => {
  let text: string | null = null;
  try {
    text = event.data?.text() ?? null;
  } catch {
    // nieczytelny ładunek — pokażemy ogólne powiadomienie
  }
  const payload = parsePushPayload(text);
  // Subskrypcja ma `userVisibleOnly: true` — każde push musi pokazać powiadomienie.
  event.waitUntil(
    sw.registration.showNotification(payload.title, {
      body: payload.body,
      // Ten sam tag zastępuje poprzednie powiadomienie (grupowanie); `renotify` znów sygnalizuje.
      tag: payload.tag ?? undefined,
      renotify: payload.tag !== null,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: payload.url, type: payload.type },
      lang: "pl",
    } as NotificationOptions),
  );
});

sw.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const data = event.notification.data as { url?: unknown } | null;
  const target = resolveClickUrl(data?.url, sw.location.origin);
  event.waitUntil(
    (async () => {
      const windows = await sw.clients.matchAll({ type: "window", includeUncontrolled: true });
      const existing = pickWindow(windows, target);
      if (!existing) {
        await sw.clients.openWindow(target);
        return;
      }
      // Bez nawigacji: przeładowanie przerwałoby np. pisaną właśnie wiadomość w czacie.
      await existing.focus();
    })(),
  );
});
