import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from "./TokenPages";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

const body = (fetch: ReturnType<typeof mockFetch>, call = -1) =>
  JSON.parse(fetch.mock.calls.at(call)![1]!.body as string);

describe("Zapomniałem hasła", () => {
  it("wysyła prośbę i pokazuje odpowiedź serwera", async () => {
    const fetch = mockFetch({
      "GET /api/auth/config": { mail_enabled: true },
      "POST /api/auth/password-reset": () =>
        jsonResponse({ message: "Jeśli konto z tym adresem istnieje, wysłaliśmy link." }, 202),
    });
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password" });

    await userEvent.type(screen.getByLabelText("E-mail"), "ala@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Wyślij link" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Jeśli konto z tym adresem");
    expect(body(fetch)).toEqual({ email: "ala@example.com" });
  });

  it("informuje o niedostępnej wysyłce maili", async () => {
    const fetch = mockFetch({ "GET /api/auth/config": { mail_enabled: false } });
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password" });

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Wysyłka e-maili jest chwilowo niedostępna",
    );
    expect(screen.queryByRole("button", { name: "Wyślij link" })).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("pokazuje limit prób", async () => {
    mockFetch({
      "GET /api/auth/config": { mail_enabled: true },
      "POST /api/auth/password-reset": () =>
        jsonResponse({ detail: "Zbyt wiele prób. Spróbuj ponownie za 12 min." }, 429),
    });
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password" });

    await userEvent.type(screen.getByLabelText("E-mail"), "ala@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Wyślij link" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Zbyt wiele prób");
  });
});

describe("nowe hasło z linku", () => {
  it("wysyła token z fragmentu adresu i nowe hasło", async () => {
    const fetch = mockFetch({
      "POST /api/auth/password-reset/confirm": { message: "Hasło zostało zmienione." },
    });
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password#token=abc-123" });

    await userEvent.type(screen.getByLabelText("Nowe hasło"), "nowe-haslo-1");
    await userEvent.type(screen.getByLabelText("Powtórz hasło"), "nowe-haslo-1");
    await userEvent.click(screen.getByRole("button", { name: "Ustaw hasło" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Hasło zostało zmienione.");
    expect(body(fetch)).toEqual({ token: "abc-123", password: "nowe-haslo-1" });
    expect(screen.getByRole("link", { name: "Przejdź do logowania" })).toBeInTheDocument();
  });

  it("sprawdza powtórzenie hasła przed wysłaniem", async () => {
    const fetch = mockFetch({});
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password#token=abc" });

    await userEvent.type(screen.getByLabelText("Nowe hasło"), "nowe-haslo-1");
    await userEvent.type(screen.getByLabelText("Powtórz hasło"), "nowe-haslo-2");
    await userEvent.click(screen.getByRole("button", { name: "Ustaw hasło" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Hasła się różnią.");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("przy wygasłym linku proponuje nowy", async () => {
    mockFetch({
      "POST /api/auth/password-reset/confirm": () =>
        jsonResponse({ detail: "Link jest nieprawidłowy.", code: "invalid_token" }, 400),
    });
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password#token=stary" });

    await userEvent.type(screen.getByLabelText("Nowe hasło"), "nowe-haslo-1");
    await userEvent.type(screen.getByLabelText("Powtórz hasło"), "nowe-haslo-1");
    await userEvent.click(screen.getByRole("button", { name: "Ustaw hasło" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Link jest nieprawidłowy.");
    expect(screen.getByRole("link", { name: "Wyślij nowy link" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });

  it("bez tokenu pokazuje błąd linku", () => {
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password" });

    expect(screen.getByRole("alert")).toHaveTextContent("Link jest niepełny");
  });
});

describe("potwierdzenie adresu", () => {
  it("potwierdza dopiero po kliknięciu", async () => {
    const fetch = mockFetch({
      "POST /api/auth/verify-email": {
        message: "Adres potwierdzony. Od teraz logujesz się adresem e-mail.",
      },
    });
    renderWithProviders(<VerifyEmailPage />, { route: "/verify-email#token=tok" });

    expect(fetch).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Potwierdź adres" }));

    expect(await screen.findByRole("status")).toHaveTextContent("logujesz się adresem e-mail");
    expect(body(fetch)).toEqual({ token: "tok" });
  });

  it("przy zużytym linku odsyła do profilu", async () => {
    mockFetch({
      "POST /api/auth/verify-email": () =>
        jsonResponse({ detail: "Link wygasł albo został już użyty.", code: "invalid_token" }, 400),
    });
    renderWithProviders(<VerifyEmailPage />, { route: "/verify-email#token=tok" });

    await userEvent.click(screen.getByRole("button", { name: "Potwierdź adres" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("został już użyty");
    expect(screen.queryByRole("button", { name: "Potwierdź adres" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "profil" })).toHaveAttribute("href", "/profile");
  });
});
