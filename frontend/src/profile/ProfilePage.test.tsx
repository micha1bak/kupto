import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Profile } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import { ProfilePage } from "./ProfilePage";

const profile: Profile = { id: 1, login: "ala", name: "Ala", household: { id: 1, name: "Dom" } };

afterEach(() => vi.unstubAllGlobals());

describe("strona profilu", () => {
  it("pokazuje imię, login, gospodarstwo i linki przeniesione z paska", () => {
    renderWithProviders(<ProfilePage profile={profile} onLogout={vi.fn()} />, { route: "/profile" });

    expect(screen.getByRole("heading", { name: "Ala" })).toBeInTheDocument();
    expect(screen.getByText("Login: ala")).toBeInTheDocument();
    expect(screen.getByText("Gospodarstwo „Dom”")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Wróć do listy" })).toHaveAttribute("href", "/");

    const links = {
      "/household": /^Gospodarstwo/,
      "/history": "Historia zakupów",
      "/recipes": "Przepisy",
      "/meal-plan": "Plan obiadów",
    };
    for (const [href, name] of Object.entries(links)) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", href);
    }
    expect(screen.getByRole("link", { name: /^Gospodarstwo/ })).toHaveTextContent(
      "preferencje, powiadomienia",
    );
  });

  it("zmienia imię", async () => {
    const fetch = mockFetch({
      "PATCH /api/users/me": () => jsonResponse({ ...profile, name: "Ala K." }),
    });
    const { queryClient } = renderWithProviders(
      <ProfilePage profile={profile} onLogout={vi.fn()} />,
      { route: "/profile" },
    );

    const field = screen.getByLabelText("Imię");
    expect(field).toHaveValue("Ala");
    await userEvent.clear(field);
    await userEvent.type(field, "Ala K.");
    await userEvent.click(screen.getByRole("button", { name: "Zmień imię" }));

    await vi.waitFor(() => expect(queryClient.getQueryData(["profile"])).toMatchObject({ name: "Ala K." }));
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({ name: "Ala K." });
  });

  it("nie zapisuje pustego imienia", async () => {
    const fetch = mockFetch({});
    renderWithProviders(<ProfilePage profile={profile} onLogout={vi.fn()} />, { route: "/profile" });

    await userEvent.clear(screen.getByLabelText("Imię"));
    await userEvent.type(screen.getByLabelText("Imię"), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Zmień imię" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Podaj imię.");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("„Wyloguj” wylogowuje", async () => {
    const onLogout = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(<ProfilePage profile={profile} onLogout={onLogout} />, { route: "/profile" });

    await userEvent.click(screen.getByRole("button", { name: "Wyloguj" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });
});
