import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EmailBanner } from "./EmailBanner";
import { EmailGate } from "./EmailGate";
import { EmailSection } from "./EmailSection";
import { jsonResponse, mockFetch, renderWithProviders, testProfile } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

const unverified = testProfile({
  email_verified: false,
  email_status: "unverified",
  verify_email_by: "2026-10-31T12:00:00Z",
});
const legacy = testProfile({
  login: "stary",
  email: null,
  email_verified: false,
  email_status: "missing",
  email_blocked: true,
});

describe("ekran adresu e-mail", () => {
  it("stare konto podaje adres, a profil w cache się zmienia", async () => {
    const after = { ...legacy, email: "stary@example.com", email_status: "unverified", email_blocked: false };
    const fetch = mockFetch({ "POST /api/users/me/email": () => jsonResponse(after) });
    const { queryClient } = renderWithProviders(<EmailGate profile={legacy} onLogout={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Podaj adres e-mail" })).toBeInTheDocument();
    expect(screen.getByText(/loginem „stary”/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Adres e-mail"), "Stary@Example.com");
    await userEvent.click(screen.getByRole("button", { name: "Wyślij link" }));

    await vi.waitFor(() => expect(queryClient.getQueryData(["profile"])).toEqual(after));
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
      email: "Stary@Example.com",
    });
  });

  it("nie wysyła niepoprawnego adresu", async () => {
    const fetch = mockFetch({});
    renderWithProviders(<EmailGate profile={legacy} onLogout={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Adres e-mail"), "stary");
    await userEvent.click(screen.getByRole("button", { name: "Wyślij link" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Podaj poprawny adres e-mail.");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("po terminie pozwala wysłać link ponownie i wylogować się", async () => {
    const blocked = { ...unverified, email_blocked: true };
    const fetch = mockFetch({ "POST /api/users/me/email": blocked });
    const onLogout = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(<EmailGate profile={blocked} onLogout={onLogout} />);

    expect(screen.getByRole("heading", { name: "Potwierdź adres e-mail" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Wyślij link ponownie" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Wysłaliśmy nowy link");
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
      email: "ala@example.com",
    });
    await userEvent.click(screen.getByRole("button", { name: "Wyloguj" }));
    expect(onLogout).toHaveBeenCalledOnce();
  });
});

describe("baner potwierdzenia adresu", () => {
  it("przypomina o adresie i terminie", () => {
    renderWithProviders(<EmailBanner profile={unverified} />);

    expect(screen.getByRole("complementary", { name: "Potwierdzenie adresu e-mail" })).toHaveTextContent(
      /Potwierdź adres ala@example.com.*31 października/,
    );
  });

  it.each([
    ["potwierdzony adres", testProfile()],
    ["wysyłka niedostępna", { ...unverified, mail_enabled: false }],
  ])("nie pojawia się, gdy %s", (_, profile) => {
    renderWithProviders(<EmailBanner profile={profile} />);

    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });
});

describe("adres na profilu", () => {
  it("bez wysyłki maili informuje, że potwierdzenie będzie później", () => {
    renderWithProviders(
      <EmailSection profile={{ ...legacy, email_blocked: false, mail_enabled: false }} />,
    );

    expect(screen.getByText(/Wysyłka e-maili jest jeszcze niedostępna/)).toBeInTheDocument();
    expect(screen.getByText(/loginem „stary”/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Adres e-mail")).not.toBeInTheDocument();
  });

  it("niepotwierdzony adres można zmienić", async () => {
    const fetch = mockFetch({ "POST /api/users/me/email": { ...unverified, email: "nowy@example.com" } });
    renderWithProviders(<EmailSection profile={unverified} />);

    const field = screen.getByLabelText("Adres e-mail");
    await userEvent.clear(field);
    await userEvent.type(field, "nowy@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Zmień adres" }));

    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({ email: "nowy@example.com" });
  });
});
