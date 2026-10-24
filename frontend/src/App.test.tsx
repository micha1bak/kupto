import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { FakeEventSource } from "./test/fakeEventSource";
import { jsonResponse, mockFetch } from "./test/utils";

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
      jsonResponse({ id: 2, login: "ola", household: removed ? null : { id: 1, name: "Dom" } }),
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
    "GET /api/users/me": { id: 1, login: "ala", household: { id: 1, name: "Dom" } },
    "POST /api/auth/logout": () => jsonResponse(null, 204),
  });
  window.history.pushState({}, "", "/profile");
  render(<App />);

  await userEvent.click(await screen.findByRole("button", { name: "Wyloguj" }));

  expect(await screen.findByRole("button", { name: "Zaloguj" })).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" }));
});

test("user without household sees setup", async () => {
  mockFetch({ "GET /api/users/me": { id: 1, login: "ala", household: null } });
  window.history.pushState({}, "", "/");

  render(<App />);

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});
