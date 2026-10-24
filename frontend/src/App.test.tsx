import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { FakeEventSource } from "./test/fakeEventSource";
import { jsonResponse, mockFetch, testProfile } from "./test/utils";

afterEach(() => vi.unstubAllGlobals());

test("unauthenticated user is redirected to login", async () => {
  mockFetch({ "GET /api/users/me": () => jsonResponse({ detail: "Wymagane zalogowanie." }, 401) });

  render(<App />);

  expect(await screen.findByRole("button", { name: "Zaloguj" })).toBeInTheDocument();
});

test("member removed from household is moved to setup instead of a stale list", async () => {
  let removed = false;
  mockFetch({
    "GET /api/users/me": () =>
      jsonResponse({ id: 2, login: "ola", name: "Ola", household: removed ? null : { id: 1, name: "Dom" } }),
    "GET /api/chat/messages": [],
    "GET /api/list": () =>
      removed
        ? jsonResponse({ detail: "Najpierw utwórz gospodarstwo.", code: "no_household" }, 409)
        : jsonResponse({ id: 1, groups: [] }),
  });
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  window.history.pushState({}, "", "/");
  render(<App />);
  await screen.findByRole("heading", { name: "Lista" });
  act(() => FakeEventSource.last.emit("ready"));

  // Właściciel usuwa olę: serwer kończy jej strumień zmian, a ponowne połączenie dostaje 409,
  // więc przeglądarka zamyka strumień na dobre — lista jest pobierana ponownie i dostaje 409.
  removed = true;
  act(() => FakeEventSource.last.fail({ closed: true }));

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});

test("profile page logs out to the login screen", async () => {
  const fetch = mockFetch({
    "GET /api/users/me": { id: 1, login: "ala", name: "Ala", household: { id: 1, name: "Dom" } },
    "POST /api/auth/logout": () => jsonResponse(null, 204),
  });
  window.history.pushState({}, "", "/profile");
  render(<App />);

  await userEvent.click(await screen.findByRole("button", { name: "Wyloguj" }));

  expect(await screen.findByRole("button", { name: "Zaloguj" })).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" }));
});

test("user without household sees setup", async () => {
  mockFetch({ "GET /api/users/me": { id: 1, login: "ala", name: "Ala", household: null } });
  window.history.pushState({}, "", "/");

  render(<App />);

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});

test("account without a name must fill it in before using the app", async () => {
  let name: string | null = null;
  const fetch = mockFetch({
    "GET /api/users/me": () => jsonResponse({ id: 1, login: "ala", name, household: null }),
    "PATCH /api/users/me": (_url: string, init: RequestInit) => {
      name = JSON.parse(init.body as string).name;
      return jsonResponse({ id: 1, login: "ala", name, household: null });
    },
  });
  window.history.pushState({}, "", "/");
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Jak masz na imię?" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Utwórz gospodarstwo" })).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Imię"), "  Ala ");
  await userEvent.click(screen.getByRole("button", { name: "Zapisz" }));

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
  const patch = fetch.mock.calls.find(([, init]) => init?.method === "PATCH")!;
  expect(JSON.parse(patch[1]!.body as string)).toEqual({ name: "Ala" });
});

test("legacy account must give an address before choosing a household", async () => {
  let profile = testProfile({
    login: "stary",
    email: null,
    email_verified: false,
    email_status: "missing",
    email_blocked: true,
    household: null,
  });
  mockFetch({
    "GET /api/users/me": () => jsonResponse(profile),
    "POST /api/users/me/email": () => {
      profile = { ...profile, email: "stary@example.com", email_status: "unverified", email_blocked: false };
      return jsonResponse(profile);
    },
  });
  window.history.pushState({}, "", "/");
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Podaj adres e-mail" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Utwórz gospodarstwo" })).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Adres e-mail"), "stary@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Wyślij link" }));

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});

test("expired verification deadline during use shows the confirmation screen", async () => {
  let blocked = false;
  const profile = () =>
    testProfile({
      email_verified: false,
      email_status: "unverified",
      verify_email_by: "2026-10-24T12:00:00Z",
      email_blocked: blocked,
    });
  mockFetch({
    "GET /api/users/me": () => jsonResponse(profile()),
    "GET /api/chat/messages": () => {
      blocked = true;
      return jsonResponse({ detail: "Potwierdź adres e-mail.", code: "email_unverified" }, 403);
    },
    "GET /api/chat/archive": [],
    "GET /api/list": () =>
      jsonResponse({ detail: "Potwierdź adres e-mail.", code: "email_unverified" }, 403),
  });
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  window.history.pushState({}, "", "/");
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Potwierdź adres e-mail" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Wyślij link ponownie" })).toBeInTheDocument();
});

test.each(["/forgot-password", "/reset-password", "/verify-email"])(
  "%s is available without a session",
  async (path) => {
    mockFetch({ "GET /api/auth/config": { mail_enabled: true } });
    window.history.pushState({}, "", path);

    render(<App />);

    expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
  },
);
