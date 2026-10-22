import type { Plugin } from "vite";

/** Pliki z `public/` należące do powłoki (nie przechodzą przez bundler, więc lista jest jawna). */
export const PUBLIC_SHELL_FILES = [
  "/manifest.webmanifest",
  "/icons/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png",
];

const SW_SOURCE = "src/pwa/sw.ts";
const SW_FILE = "sw.js";

/** Lista precache: dokument (`/`), wszystkie pliki z `assets/` bieżącego buildu i pliki z `public/`. */
export function precacheList(bundleFiles: Iterable<string>): string[] {
  const assets = [...bundleFiles].filter((f) => f.startsWith("assets/")).map((f) => `/${f}`);
  return ["/", ...assets.sort(), ...PUBLIC_SHELL_FILES];
}

/**
 * Wersja = skrót listy (nazwy plików w `assets/` zawierają hash treści) i kodu samego SW.
 * FNV-1a (64 bity) wystarcza do rozróżnienia buildów i nie wymaga typów Node w projekcie.
 */
export function shellVersion(list: string[], swCode: string): string {
  const text = JSON.stringify(list) + swCode;
  let hash = 0xcbf29ce484222325n;
  for (let i = 0; i < text.length; i++) {
    hash = BigInt.asUintN(64, (hash ^ BigInt(text.charCodeAt(i))) * 0x100000001b3n);
  }
  return hash.toString(16).padStart(16, "0");
}

/**
 * Buduje `src/pwa/sw.ts` do `dist/sw.js` (stała nazwa, bez hasha) i wstawia listę precache oraz
 * wersję. Tylko `vite build` — w trybie deweloperskim SW nie jest rejestrowany.
 */
export function serviceWorkerPlugin(): Plugin {
  return {
    name: "kupto-service-worker",
    apply: "build",
    buildStart() {
      this.emitFile({ type: "chunk", id: SW_SOURCE, fileName: SW_FILE });
    },
    generateBundle(_options, bundle) {
      const sw = bundle[SW_FILE];
      if (!sw || sw.type !== "chunk") this.error(`Brak ${SW_FILE} w buildzie`);
      if (sw.imports.length > 0) this.error(`${SW_FILE} nie może importować innych kawałków`);
      const list = precacheList(Object.keys(bundle).filter((f) => f !== SW_FILE));
      const version = shellVersion(list, sw.code);
      const code = sw.code
        .replaceAll("__KUPTO_PRECACHE__", JSON.stringify(list))
        .replaceAll("__KUPTO_SW_VERSION__", JSON.stringify(version));
      if (code === sw.code) this.error(`Nie znaleziono znaczników w ${SW_FILE}`);
      sw.code = code;
    },
  };
}
