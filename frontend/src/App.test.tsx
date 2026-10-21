import { render, screen } from "@testing-library/react";
import { App } from "./App";
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
  window.history.pushState({}, "", "/");
  render(<App />);
  await screen.findByRole("heading", { name: "Lista" });

  removed = true; // właściciel usuwa olę; kolejny polling listy dostaje 409 no_household

  expect(
    await screen.findByRole("heading", { name: "Utwórz gospodarstwo" }, { timeout: 8000 }),
  ).toBeInTheDocument();
}, 10_000);

test("user without household sees setup", async () => {
  mockFetch({ "GET /api/users/me": { id: 1, login: "ala", household: null } });
  window.history.pushState({}, "", "/");

  render(<App />);

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});
