import { describe, expect, it, vi } from "vitest";
import {
  DISMISS_FOR_MS,
  DISMISS_KEY,
  bannerVariant,
  captureInstallPrompt,
  clearInstallPrompt,
  getInstallPrompt,
  isDismissed,
  isIos,
  isStandalone,
  rememberDismissal,
} from "./install";

const UA = {
  iphone:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
  ipad: "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
  mac: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
  android:
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
};

const nav = (userAgent: string, platform = "", maxTouchPoints = 0, standalone?: boolean) => ({
  userAgent,
  platform,
  maxTouchPoints,
  standalone,
});

describe("isIos", () => {
  it("rozpoznaje iPhone'a, iPada i iPadOS udającego Maca", () => {
    expect(isIos(nav(UA.iphone, "iPhone"))).toBe(true);
    expect(isIos(nav(UA.ipad, "iPad"))).toBe(true);
    expect(isIos(nav(UA.mac, "MacIntel", 5))).toBe(true);
  });

  it("nie myli Maca ani Androida z iOS", () => {
    expect(isIos(nav(UA.mac, "MacIntel", 0))).toBe(false);
    expect(isIos(nav(UA.android, "Linux armv8l", 5))).toBe(false);
  });
});

describe("isStandalone", () => {
  const win = (matching: string | null, standalone?: boolean) => ({
    navigator: nav(UA.android, "", 0, standalone),
    matchMedia: (query: string) => ({ matches: query === matching }) as MediaQueryList,
  });

  it("wykrywa display-mode standalone (Android, desktop)", () => {
    expect(isStandalone(win("(display-mode: standalone)"))).toBe(true);
  });

  it("wykrywa navigator.standalone (iOS)", () => {
    expect(isStandalone(win(null, true))).toBe(true);
  });

  it("w zwykłej karcie przeglądarki zwraca false", () => {
    expect(isStandalone(win("(display-mode: browser)"))).toBe(false);
  });
});

describe("zamknięcie banera", () => {
  it("jest pamiętane przez 30 dni", () => {
    const now = 1_000_000_000_000;
    rememberDismissal(localStorage, now);
    expect(localStorage.getItem(DISMISS_KEY)).toBe(String(now));
    expect(isDismissed(localStorage, now + 1000)).toBe(true);
    expect(isDismissed(localStorage, now + DISMISS_FOR_MS + 1)).toBe(false);
    localStorage.clear();
  });

  it("bez zapisu lub z błędną wartością baner nie jest zamknięty", () => {
    expect(isDismissed(localStorage, Date.now())).toBe(false);
    localStorage.setItem(DISMISS_KEY, "abc");
    expect(isDismissed(localStorage, Date.now())).toBe(false);
    localStorage.clear();
  });

  it("niedostępny localStorage nie rzuca wyjątków", () => {
    const broken = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
    } as unknown as Storage;
    expect(isDismissed(broken, Date.now())).toBe(false);
    expect(() => rememberDismissal(broken, Date.now())).not.toThrow();
    expect(isDismissed(undefined, Date.now())).toBe(false);
  });
});

describe("bannerVariant", () => {
  const base = { standalone: false, dismissed: false, canPrompt: false, ios: false };

  it("przycisk instalacji, gdy przeglądarka zgłosiła możliwość instalacji", () => {
    expect(bannerVariant({ ...base, canPrompt: true })).toBe("prompt");
  });

  it("instrukcja na iOS", () => {
    expect(bannerVariant({ ...base, ios: true })).toBe("ios");
  });

  it("nic w trybie standalone, po zamknięciu i bez możliwości instalacji", () => {
    expect(bannerVariant({ ...base, ios: true, standalone: true })).toBeNull();
    expect(bannerVariant({ ...base, canPrompt: true, dismissed: true })).toBeNull();
    expect(bannerVariant(base)).toBeNull();
  });
});

describe("captureInstallPrompt", () => {
  it("przechwytuje beforeinstallprompt i czyści je po instalacji", () => {
    const target = new EventTarget();
    captureInstallPrompt(target as unknown as Window);
    const event = new Event("beforeinstallprompt", { cancelable: true });
    const preventDefault = vi.spyOn(event, "preventDefault");
    target.dispatchEvent(event);
    expect(preventDefault).toHaveBeenCalled();
    expect(getInstallPrompt()).toBe(event);
    target.dispatchEvent(new Event("appinstalled"));
    expect(getInstallPrompt()).toBeNull();
    clearInstallPrompt();
  });
});
