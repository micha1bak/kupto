/**
 * Powiadomienia w service workerze (design D8). Czyste funkcje — bez API przeglądarki, żeby dało
 * się je testować w Vitest i współdzielić tylko z `sw.ts`.
 */

/** Ładunek wysyłany przez backend (`kupto.push.notification.Notification.payload`). */
export interface PushPayload {
  title: string;
  body: string;
  url: string;
  tag: string | null;
  type: string | null;
}

const FALLBACK: PushPayload = { title: "Kupto", body: "", url: "/", tag: null, type: null };

const str = (value: unknown): string | null => (typeof value === "string" ? value : null);

/** Odczyt ładunku; uszkodzony lub pusty → ogólne „Kupto” (powiadomienie i tak musi się pokazać). */
export function parsePushPayload(text: string | null | undefined): PushPayload {
  if (!text) return FALLBACK;
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return FALLBACK;
  }
  if (typeof data !== "object" || data === null) return FALLBACK;
  const record = data as Record<string, unknown>;
  return {
    title: str(record.title) || FALLBACK.title,
    body: str(record.body) ?? "",
    url: str(record.url) ?? "/",
    tag: str(record.tag) || null,
    type: str(record.type),
  };
}

/** Adres do otwarcia po kliknięciu — tylko w obrębie aplikacji (inna domena → strona główna). */
export function resolveClickUrl(url: unknown, origin: string): string {
  try {
    const resolved = new URL(typeof url === "string" ? url : "/", origin);
    return resolved.origin === origin ? resolved.href : `${origin}/`;
  } catch {
    return `${origin}/`;
  }
}

export interface WindowLike {
  url: string;
}

/** Okno aplikacji do pokazania po kliknięciu: najlepiej to z docelowym adresem, inaczej dowolne. */
export function pickWindow<T extends WindowLike>(windows: readonly T[], target: string): T | undefined {
  return windows.find((w) => w.url === target) ?? windows[0];
}
