import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthForm } from "./AuthForm";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

async function fill(login: string, password: string) {
  await userEvent.type(screen.getByLabelText("Login"), login);
  await userEvent.type(screen.getByLabelText("Hasło"), password);
}

test("register validates lengths before calling the API", async () => {
  const fetch = mockFetch({});
  renderWithProviders(<AuthForm mode="register" />);

  await fill("al", "krotkie");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Login musi mieć od 3 do 50 znaków.");
  expect(fetch).not.toHaveBeenCalled();
});

test("login shows server message on 401", async () => {
  mockFetch({
    "POST /api/auth/login": () =>
      jsonResponse({ detail: "Nieprawidłowy login lub hasło." }, 401),
  });
  renderWithProviders(<AuthForm mode="login" />);

  await fill("ala", "zle-haslo");
  await userEvent.click(screen.getByRole("button", { name: "Zaloguj" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Nieprawidłowy login lub hasło.");
});

test("register shows conflict when login is taken", async () => {
  mockFetch({
    "POST /api/auth/register": () => jsonResponse({ detail: "Ten login jest już zajęty." }, 409),
  });
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Ten login jest już zajęty.");
});

test("successful register logs the user in", async () => {
  const fetch = mockFetch({
    "POST /api/auth/register": () => jsonResponse({ message: "ok" }, 201),
    "POST /api/auth/login": { message: "ok" },
  });
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
    login: "ala",
    password: "haslo1234",
  });
});
