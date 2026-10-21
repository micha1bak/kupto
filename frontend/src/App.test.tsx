import { render, screen } from "@testing-library/react";
import { App } from "./App";
import { jsonResponse, mockFetch } from "./test/utils";

afterEach(() => vi.unstubAllGlobals());

test("unauthenticated user is redirected to login", async () => {
  mockFetch({ "GET /api/users/me": () => jsonResponse({ detail: "Wymagane zalogowanie." }, 401) });

  render(<App />);

  expect(await screen.findByRole("button", { name: "Zaloguj" })).toBeInTheDocument();
});

test("user without household sees setup", async () => {
  mockFetch({ "GET /api/users/me": { id: 1, login: "ala", household: null } });
  window.history.pushState({}, "", "/");

  render(<App />);

  expect(await screen.findByRole("heading", { name: "Utwórz gospodarstwo" })).toBeInTheDocument();
});
