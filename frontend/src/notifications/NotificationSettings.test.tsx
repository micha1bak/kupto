import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { disablePushOnLogout, urlBase64ToBytes, type PushEnv } from "../pwa/push";
import { jsonResponse, mockFetch } from "../test/utils";
import { NotificationSettings } from "./NotificationSettings";

const SERVER_KEY = "BP" + "x".repeat(85);
const OTHER_KEY = "BA" + "A".repeat(85);
const ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc";

function fakeSubscription(key: Uint8Array, onUnsubscribe: () => void) {
  return {
    endpoint: ENDPOINT,
    options: { applicationServerKey: key.slice().buffer, userVisibleOnly: true },
    toJSON: () => ({ endpoint: ENDPOINT, expirationTime: null, keys: { p256dh: "p", auth: "a" } }),
    unsubscribe: vi.fn(async () => {
      onUnsubscribe();
      return true;
    }),
  };
}

type FakeSubscription = ReturnType<typeof fakeSubscription>;

function fakeEnv({
  permission = "default" as NotificationPermission,
  answer = "granted" as NotificationPermission,
  subscribedWith = null as string | null,
  ios = false,
  standalone = false,
  serviceWorker = true,
} = {}) {
  let subscription: FakeSubscription | null = null;
  const unsubscribe = () => {
    subscription = null;
  };
  if (subscribedWith) subscription = fakeSubscription(urlBase64ToBytes(subscribedWith), unsubscribe);
  const pushManager = {
    getSubscription: vi.fn(async () => subscription),
    subscribe: vi.fn(async (options: PushSubscriptionOptionsInit) => {
      subscription = fakeSubscription(options.applicationServerKey as Uint8Array, unsubscribe);
      return subscription;
    }),
  };
  const registration = { pushManager } as unknown as ServiceWorkerRegistration;
  const notification = {
    permission,
    requestPermission: vi.fn(async () => {
      notification.permission = answer;
      return answer;
    }),
  };
  const env: PushEnv = {
    serviceWorker: serviceWorker
      ? { getRegistration: async () => registration, ready: Promise.resolve(registration) }
      : undefined,
    notification,
    pushManager: true,
    ios,
    standalone,
  };
  return { env, pushManager, notification, current: () => subscription };
}

function serverWithKey() {
  return mockFetch({
    "GET /api/push/public-key": { public_key: SERVER_KEY },
    "PUT /api/push/subscriptions": () => jsonResponse(null, 204),
    "DELETE /api/push/subscriptions": () => jsonResponse(null, 204),
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("NotificationSettings", () => {
  it("bez obsługi Web Push informuje o tym i nie pokazuje przycisku", async () => {
    const fetch = serverWithKey();
    const { env } = fakeEnv({ serviceWorker: false });
    render(<NotificationSettings env={env} />);
    expect(await screen.findByText(/nie obsługuje powiadomień/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("na iPhonie bez instalacji prosi o dodanie do ekranu początkowego", async () => {
    const { env, notification } = fakeEnv({ ios: true, standalone: false });
    render(<NotificationSettings env={env} />);
    expect(await screen.findByText(/dodanej do ekranu początkowego/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(notification.requestPermission).not.toHaveBeenCalled();
  });

  it("na serwerze bez kluczy pokazuje, że powiadomienia są niedostępne", async () => {
    mockFetch({
      "GET /api/push/public-key": () =>
        jsonResponse({ detail: "Wyłączone", code: "push_disabled" }, 404),
    });
    const { env } = fakeEnv();
    render(<NotificationSettings env={env} />);
    expect(await screen.findByText(/niedostępne/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("pyta o zgodę dopiero po kliknięciu „Włącz powiadomienia” i zapisuje subskrypcję", async () => {
    const fetch = serverWithKey();
    const { env, notification, pushManager } = fakeEnv();
    render(<NotificationSettings env={env} />);

    const enable = await screen.findByRole("button", { name: "Włącz powiadomienia" });
    expect(notification.requestPermission).not.toHaveBeenCalled();
    expect(pushManager.subscribe).not.toHaveBeenCalled();

    await userEvent.click(enable);

    expect(notification.requestPermission).toHaveBeenCalledOnce();
    const options = pushManager.subscribe.mock.calls[0][0];
    expect(options.userVisibleOnly).toBe(true);
    expect(options.applicationServerKey).toEqual(urlBase64ToBytes(SERVER_KEY));
    const put = fetch.mock.calls.find(([, init]) => init?.method === "PUT")!;
    expect(JSON.parse(put[1]!.body as string).endpoint).toBe(ENDPOINT);
    expect(await screen.findByText(/włączone na tym urządzeniu/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Wyłącz powiadomienia" })).toBeInTheDocument();
  });

  it("po odmowie zgody pokazuje stan zablokowany z instrukcją", async () => {
    serverWithKey();
    const { env } = fakeEnv({ answer: "denied" });
    render(<NotificationSettings env={env} />);
    await userEvent.click(await screen.findByRole("button", { name: "Włącz powiadomienia" }));
    expect(await screen.findByText(/zablokowane/)).toBeInTheDocument();
    expect(screen.getByText(/ustawieniach witryny/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("zablokowane wcześniej — od razu stan zablokowany, bez pytania", async () => {
    const fetch = serverWithKey();
    const { env, notification } = fakeEnv({ permission: "denied" });
    render(<NotificationSettings env={env} />);
    expect(await screen.findByText(/zablokowane/)).toBeInTheDocument();
    expect(notification.requestPermission).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("włączone: odświeża subskrypcję na serwerze, a „Wyłącz” ją usuwa", async () => {
    const fetch = serverWithKey();
    const t = fakeEnv({ permission: "granted", subscribedWith: SERVER_KEY });
    render(<NotificationSettings env={t.env} />);

    const disable = await screen.findByRole("button", { name: "Wyłącz powiadomienia" });
    expect(fetch).toHaveBeenCalledWith("/api/push/subscriptions", expect.objectContaining({ method: "PUT" }));
    expect(t.pushManager.subscribe).not.toHaveBeenCalled();

    await userEvent.click(disable);

    const del = fetch.mock.calls.find(([, init]) => init?.method === "DELETE")!;
    expect(JSON.parse(del[1]!.body as string)).toEqual({ endpoint: ENDPOINT });
    expect(t.current()).toBeNull();
    expect(await screen.findByRole("button", { name: "Włącz powiadomienia" })).toBeInTheDocument();
  });

  it("subskrypcję dla innego klucza serwera odnawia", async () => {
    serverWithKey();
    const t = fakeEnv({ permission: "granted", subscribedWith: OTHER_KEY });
    render(<NotificationSettings env={t.env} />);
    await screen.findByRole("button", { name: "Wyłącz powiadomienia" });
    expect(t.pushManager.subscribe).toHaveBeenCalledOnce();
    expect(new Uint8Array(t.current()!.options.applicationServerKey)).toEqual(
      urlBase64ToBytes(SERVER_KEY),
    );
  });

  it("błąd zapisu pokazuje komunikat i zostawia przycisk", async () => {
    mockFetch({
      "GET /api/push/public-key": { public_key: SERVER_KEY },
      "PUT /api/push/subscriptions": () =>
        jsonResponse({ detail: "Ta przeglądarka używa nieobsługiwanej usługi powiadomień." }, 422),
    });
    const { env } = fakeEnv();
    render(<NotificationSettings env={env} />);
    await userEvent.click(await screen.findByRole("button", { name: "Włącz powiadomienia" }));
    expect(await screen.findByText(/nieobsługiwanej usługi/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Włącz powiadomienia" })).toBeEnabled();
  });
});

describe("disablePushOnLogout", () => {
  it("usuwa subskrypcję z serwera i z przeglądarki", async () => {
    const fetch = serverWithKey();
    const t = fakeEnv({ permission: "granted", subscribedWith: SERVER_KEY });
    await disablePushOnLogout(t.env);
    expect(fetch).toHaveBeenCalledWith(
      "/api/push/subscriptions",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(t.current()).toBeNull();
  });

  it("wypisuje urządzenie także przy błędzie serwera", async () => {
    mockFetch({ "DELETE /api/push/subscriptions": () => jsonResponse({ detail: "x" }, 500) });
    const t = fakeEnv({ permission: "granted", subscribedWith: SERVER_KEY });
    await expect(disablePushOnLogout(t.env)).resolves.toBeUndefined();
    expect(t.current()).toBeNull();
  });
});
