import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { disablePushOnLogout, urlBase64ToBytes, type PushEnv } from "../pwa/push";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
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

const ALL_ON = {
  types: [
    { type: "shopping_started", enabled: true },
    { type: "items_added", enabled: true },
    { type: "shopping_finished", enabled: true },
  ],
};

function serverWithKey(routes: Record<string, unknown> = {}) {
  return mockFetch({
    "GET /api/push/public-key": { public_key: SERVER_KEY },
    "PUT /api/push/subscriptions": () => jsonResponse(null, 204),
    "DELETE /api/push/subscriptions": () => jsonResponse(null, 204),
    "GET /api/push/preferences": ALL_ON,
    ...routes,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("NotificationSettings", () => {
  it("bez obsługi Web Push informuje o tym i nie pokazuje przycisku", async () => {
    const fetch = serverWithKey();
    const { env } = fakeEnv({ serviceWorker: false });
    renderWithProviders(<NotificationSettings env={env} />);
    expect(await screen.findByText(/nie obsługuje powiadomień/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("na iPhonie bez instalacji prosi o dodanie do ekranu początkowego", async () => {
    const { env, notification } = fakeEnv({ ios: true, standalone: false });
    renderWithProviders(<NotificationSettings env={env} />);
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
    renderWithProviders(<NotificationSettings env={env} />);
    expect(await screen.findByText(/niedostępne/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("pyta o zgodę dopiero po kliknięciu „Włącz powiadomienia” i zapisuje subskrypcję", async () => {
    const fetch = serverWithKey();
    const { env, notification, pushManager } = fakeEnv();
    renderWithProviders(<NotificationSettings env={env} />);

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
    renderWithProviders(<NotificationSettings env={env} />);
    await userEvent.click(await screen.findByRole("button", { name: "Włącz powiadomienia" }));
    expect(await screen.findByText(/zablokowane/)).toBeInTheDocument();
    expect(screen.getByText(/ustawieniach witryny/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("zablokowane wcześniej — od razu stan zablokowany, bez pytania", async () => {
    const fetch = serverWithKey();
    const { env, notification } = fakeEnv({ permission: "denied" });
    renderWithProviders(<NotificationSettings env={env} />);
    expect(await screen.findByText(/zablokowane/)).toBeInTheDocument();
    expect(notification.requestPermission).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("włączone: odświeża subskrypcję na serwerze, a „Wyłącz” ją usuwa", async () => {
    const fetch = serverWithKey();
    const t = fakeEnv({ permission: "granted", subscribedWith: SERVER_KEY });
    renderWithProviders(<NotificationSettings env={t.env} />);

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
    renderWithProviders(<NotificationSettings env={t.env} />);
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
      "GET /api/push/preferences": ALL_ON,
    });
    const { env } = fakeEnv();
    renderWithProviders(<NotificationSettings env={env} />);
    await userEvent.click(await screen.findByRole("button", { name: "Włącz powiadomienia" }));
    expect(await screen.findByText(/nieobsługiwanej usługi/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Włącz powiadomienia" })).toBeEnabled();
  });
});

describe("NotificationSettings — typy powiadomień", () => {
  it("pokazuje przełączniki typów ze stanem użytkownika", async () => {
    serverWithKey({
      "GET /api/push/preferences": {
        types: [
          { type: "shopping_started", enabled: false },
          { type: "items_added", enabled: true },
          { type: "shopping_finished", enabled: true },
          { type: "nieznany_typ", enabled: true },
        ],
      },
    });
    const { env } = fakeEnv();
    renderWithProviders(<NotificationSettings env={env} />);

    const started = await screen.findByRole("checkbox", { name: /Ktoś idzie na zakupy/ });
    expect(started).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Dopisano w trakcie/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Zakupy zakończone/ })).toBeChecked();
    // Typ nieznany frontendowi (nowszy backend) jest pomijany.
    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
  });

  it("zmiana przełącznika zapisuje ustawienie", async () => {
    const fetch = serverWithKey({
      "PUT /api/push/preferences/shopping_started": (_url: string, init: RequestInit) => {
        const { enabled } = JSON.parse(init.body as string);
        return jsonResponse({
          types: [{ type: "shopping_started", enabled }, ...ALL_ON.types.slice(1)],
        });
      },
    });
    const t = fakeEnv({ permission: "granted", subscribedWith: SERVER_KEY });
    renderWithProviders(<NotificationSettings env={t.env} />);

    const started = await screen.findByRole("checkbox", { name: /Ktoś idzie na zakupy/ });
    await userEvent.click(started);

    expect(fetch).toHaveBeenCalledWith(
      "/api/push/preferences/shopping_started",
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ enabled: false }) }),
    );
    await waitFor(() => expect(started).not.toBeChecked());
  });

  it("błąd zapisu przywraca przełącznik i pokazuje komunikat", async () => {
    serverWithKey({
      "PUT /api/push/preferences/items_added": () =>
        jsonResponse({ detail: "Serwer niedostępny." }, 503),
    });
    const { env } = fakeEnv();
    renderWithProviders(<NotificationSettings env={env} />);

    const added = await screen.findByRole("checkbox", { name: /Dopisano w trakcie/ });
    await userEvent.click(added);

    expect(await screen.findByText("Serwer niedostępny.")).toBeInTheDocument();
    expect(added).toBeChecked();
  });

  it("bez powiadomień na serwerze nie pokazuje przełączników ani nie pyta o ustawienia", async () => {
    const fetch = mockFetch({
      "GET /api/push/public-key": () =>
        jsonResponse({ detail: "Wyłączone", code: "push_disabled" }, 404),
    });
    const { env } = fakeEnv();
    renderWithProviders(<NotificationSettings env={env} />);
    expect(await screen.findByText(/niedostępne/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith("/api/push/preferences", expect.anything());
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
