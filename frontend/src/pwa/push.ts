/**
 * Włączanie i wyłączanie powiadomień push na tym urządzeniu (design D9).
 *
 * Zgoda przeglądarki jest pytana wyłącznie w `enablePush` (po kliknięciu), nigdy przy odczycie
 * stanu. API przeglądarki przychodzi przez `PushEnv`, żeby dało się je podmienić w testach.
 */
import { ApiError, api, put } from "../api/client";
import { isIos, isStandalone } from "./install";

export type PushState =
  | "loading"
  | "unsupported" // przeglądarka bez Web Push
  | "needs-install" // iPhone/iPad poza aplikacją dodaną do ekranu początkowego
  | "unavailable" // serwer bez kluczy albo brak service workera (np. `vite dev`)
  | "blocked" // użytkownik odmówił zgody w przeglądarce
  | "enabled"
  | "disabled";

export interface PushEnv {
  serviceWorker?: Pick<ServiceWorkerContainer, "getRegistration" | "ready">;
  notification?: {
    readonly permission: NotificationPermission;
    requestPermission(): Promise<NotificationPermission>;
  };
  pushManager: boolean;
  ios: boolean;
  standalone: boolean;
}

export const PUSH_DISABLED = "push_disabled";
const REGISTRATION_TIMEOUT_MS = 3000;
const LOGOUT_TIMEOUT_MS = 2000;

export function browserPushEnv(): PushEnv {
  return {
    serviceWorker: "serviceWorker" in navigator ? navigator.serviceWorker : undefined,
    notification: "Notification" in window ? window.Notification : undefined,
    pushManager: "PushManager" in window,
    ios: isIos(navigator),
    standalone: isStandalone(window),
  };
}

/** Stan wynikający z samej przeglądarki (bez sieci); null — trzeba sprawdzić dalej. */
export function environmentState(env: PushEnv): PushState | null {
  // Przed sprawdzeniem obsługi: Safari na iOS ma Web Push tylko w zainstalowanej aplikacji.
  if (env.ios && !env.standalone) return "needs-install";
  if (!env.serviceWorker || !env.notification || !env.pushManager) return "unsupported";
  if (env.notification.permission === "denied") return "blocked";
  return null;
}

export function urlBase64ToBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4));
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

function sameKey(a: ArrayBuffer | null | undefined, b: Uint8Array): boolean {
  if (!a || a.byteLength !== b.byteLength) return false;
  const bytes = new Uint8Array(a);
  return bytes.every((value, i) => value === b[i]);
}

async function registration(
  env: PushEnv,
  timeoutMs = REGISTRATION_TIMEOUT_MS,
): Promise<ServiceWorkerRegistration | undefined> {
  const sw = env.serviceWorker;
  if (!sw) return undefined;
  const existing = await sw.getRegistration();
  if (existing) return existing;
  // Rejestracja mogła jeszcze nie skończyć się (start aplikacji); w `vite dev` nie nastąpi wcale.
  const timeout = new Promise<undefined>((resolve) => setTimeout(resolve, timeoutMs, undefined));
  return Promise.race([sw.ready, timeout]);
}

/** Publiczny klucz VAPID albo null, gdy powiadomienia są wyłączone na serwerze. */
async function publicKey(): Promise<string | null> {
  try {
    return (await api<{ public_key: string }>("/api/push/public-key")).public_key;
  } catch (error) {
    if (error instanceof ApiError && error.code === PUSH_DISABLED) return null;
    throw error;
  }
}

function saveSubscription(subscription: PushSubscription): Promise<void> {
  return put<void>("/api/push/subscriptions", subscription.toJSON());
}

function deleteSubscription(endpoint: string): Promise<void> {
  return api<void>("/api/push/subscriptions", {
    method: "DELETE",
    body: JSON.stringify({ endpoint }),
  });
}

/**
 * Bieżący stan bez pytania o zgodę. Istniejąca subskrypcja jest przy okazji ponownie zapisywana
 * na serwerze (przypisanie do zalogowanego, odtworzenie po wygaśnięciu), a powstała dla innego
 * klucza serwera — odnawiana.
 */
export async function readPushState(env: PushEnv): Promise<PushState> {
  const fromEnv = environmentState(env);
  if (fromEnv) return fromEnv;
  const reg = await registration(env);
  if (!reg) return "unavailable";
  const key = await publicKey();
  if (!key) return "unavailable";
  let subscription = await reg.pushManager.getSubscription();
  if (!subscription || env.notification!.permission !== "granted") return "disabled";
  const serverKey = urlBase64ToBytes(key);
  if (!sameKey(subscription.options.applicationServerKey, serverKey)) {
    await subscription.unsubscribe();
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: serverKey,
    });
  }
  await saveSubscription(subscription);
  return "enabled";
}

/** Po kliknięciu „Włącz powiadomienia”: zgoda, subskrypcja, zapis na serwerze. */
export async function enablePush(env: PushEnv): Promise<PushState> {
  const fromEnv = environmentState(env);
  if (fromEnv) return fromEnv;
  // Najpierw zgoda — Safari wymaga, by prośba wyszła bezpośrednio z kliknięcia.
  const permission = await env.notification!.requestPermission();
  if (permission === "denied") return "blocked";
  if (permission !== "granted") return "disabled"; // okno zamknięte bez decyzji
  const reg = await registration(env);
  if (!reg) return "unavailable";
  const key = await publicKey();
  if (!key) return "unavailable";
  const subscription = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToBytes(key),
  });
  await saveSubscription(subscription);
  return "enabled";
}

/** „Wyłącz powiadomienia”: usunięcie z serwera, potem z przeglądarki. */
export async function disablePush(env: PushEnv): Promise<PushState> {
  const reg = env.serviceWorker ? await registration(env, 0) : undefined;
  const subscription = await reg?.pushManager.getSubscription();
  if (subscription) {
    await deleteSubscription(subscription.endpoint);
    await subscription.unsubscribe();
  }
  return environmentState(env) ?? "disabled";
}

/**
 * Przy wylogowaniu: urządzenie przestaje dostawać powiadomienia tego użytkownika. Nie zgłasza
 * błędów i nie wstrzymuje wylogowania dłużej niż `LOGOUT_TIMEOUT_MS`.
 */
export async function disablePushOnLogout(env: PushEnv = browserPushEnv()): Promise<void> {
  if (!env.serviceWorker || !env.pushManager) return;
  const work = (async () => {
    const reg = await registration(env, 0);
    const subscription = await reg?.pushManager.getSubscription();
    if (!subscription) return;
    // Nawet gdy serwer nie odpowie, wypisanie w przeglądarce unieważnia subskrypcję (serwer
    // dostanie 410 przy następnej wysyłce i ją usunie).
    await deleteSubscription(subscription.endpoint).catch(() => undefined);
    await subscription.unsubscribe();
  })().catch(() => undefined);
  const timeout = new Promise<void>((resolve) => setTimeout(resolve, LOGOUT_TIMEOUT_MS));
  await Promise.race([work, timeout]);
}
