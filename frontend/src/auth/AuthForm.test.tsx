import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthForm } from "./AuthForm";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

async function fill(email: string, password: string, name = "Ala") {
  const nameField = screen.queryByLabelText("Imię");
  if (nameField && name) await userEvent.type(nameField, name);
  await userEvent.type(screen.getByLabelText("E-mail"), email);
  await userEvent.type(screen.getByLabelText("Hasło"), password);
}

test("register validates the address before calling the API", async () => {
  const fetch = mockFetch({});
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Podaj poprawny adres e-mail.");
  expect(fetch).not.toHaveBeenCalled();
});

test("register validates password length before calling the API", async () => {
  const fetch = mockFetch({});
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala@example.com", "krotkie");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Hasło musi mieć co najmniej 8 znaków.");
  expect(fetch).not.toHaveBeenCalled();
});

test("login shows server message on 401", async () => {
  mockFetch({
    "POST /api/auth/login": () => jsonResponse({ detail: "Nieprawidłowy e-mail lub hasło." }, 401),
  });
  renderWithProviders(<AuthForm mode="login" />);

  await fill("ala@example.com", "zle-haslo");
  await userEvent.click(screen.getByRole("button", { name: "Zaloguj" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Nieprawidłowy e-mail lub hasło.");
});

test("login accepts a legacy login in the address field", async () => {
  const fetch = mockFetch({ "POST /api/auth/login": { message: "ok" } });
  renderWithProviders(<AuthForm mode="login" />);

  expect(screen.getByText(/dawny login/)).toBeInTheDocument();
  await fill("stary", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zaloguj" }));

  await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
    email: "stary",
    password: "haslo1234",
  });
});

test("register shows conflict when the address is taken", async () => {
  mockFetch({
    "POST /api/auth/register": () =>
      jsonResponse({ detail: "Konto z tym adresem e-mail już istnieje." }, 409),
  });
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala@example.com", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Konto z tym adresem e-mail już istnieje.",
  );
});

test("successful register logs the user in", async () => {
  const fetch = mockFetch({
    "POST /api/auth/register": () => jsonResponse({ message: "ok" }, 201),
    "POST /api/auth/login": { message: "ok" },
  });
  renderWithProviders(<AuthForm mode="register" />);

  await fill(" ala@example.com ", "haslo1234");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
    email: "ala@example.com",
    password: "haslo1234",
    name: "Ala",
  });
  expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
    email: "ala@example.com",
    password: "haslo1234",
  });
});

test("register requires a name", async () => {
  const fetch = mockFetch({});
  renderWithProviders(<AuthForm mode="register" />);

  await fill("ala@example.com", "haslo1234", "");
  await userEvent.click(screen.getByRole("button", { name: "Zarejestruj" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Podaj imię.");
  expect(fetch).not.toHaveBeenCalled();
});

test("login form does not ask for a name and links to password reset", () => {
  renderWithProviders(<AuthForm mode="login" />);

  expect(screen.queryByLabelText("Imię")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Zapomniałem hasła" })).toHaveAttribute(
    "href",
    "/forgot-password",
  );
});
