import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Profile } from "../api/types";
import { renderWithProviders } from "../test/utils";
import { ProfilePage } from "./ProfilePage";

const profile: Profile = { id: 1, login: "ala", household: { id: 1, name: "Dom" } };

describe("strona profilu", () => {
  it("pokazuje login, gospodarstwo i linki przeniesione z paska", () => {
    renderWithProviders(<ProfilePage profile={profile} onLogout={vi.fn()} />, { route: "/profile" });

    expect(screen.getByRole("heading", { name: "ala" })).toBeInTheDocument();
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

  it("„Wyloguj” wylogowuje", async () => {
    const onLogout = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(<ProfilePage profile={profile} onLogout={onLogout} />, { route: "/profile" });

    await userEvent.click(screen.getByRole("button", { name: "Wyloguj" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });
});
