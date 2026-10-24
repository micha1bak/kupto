import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Profile } from "../api/types";
import { FakeEventSource } from "../test/fakeEventSource";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import { MainPage } from "./MainPage";

const profile: Profile = { id: 1, login: "ala", name: "Ala", household: { id: 1, name: "Dom" } };
const message = { id: 1, role: "user", content: "stara wiadomość", created_at: "" };

function renderMain(routes: Record<string, unknown> = {}, who: Profile = profile) {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  const fetch = mockFetch({
    "GET /api/chat/messages": [message],
    "GET /api/chat/archive": [],
    "GET /api/list": { id: 1, groups: [], shoppers: [] },
    ...routes,
  });
  renderWithProviders(<MainPage profile={who} />);
  return fetch;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("pasek nawigacji", () => {
  it("ma tylko „Kupto”, tytuł czatu i ikonę profilu", () => {
    renderMain();
    const bar = screen.getByRole("banner");

    expect(within(bar).getByRole("link", { name: "Kupto" })).toHaveAttribute("href", "/");
    const title = within(bar).getByRole("button", { name: "Dom" });
    expect(title).toHaveAttribute("aria-haspopup", "dialog");
    expect(title).toHaveAttribute("aria-expanded", "false");
    expect(within(bar).getByRole("link", { name: "Profil" })).toHaveAttribute("href", "/profile");

    expect(within(bar).getAllByRole("link")).toHaveLength(2);
    expect(within(bar).getAllByRole("button")).toHaveLength(1);
    // Dawne elementy paska są teraz na profilu albo w opcjach czatu.
    for (const gone of ["Przepisy", "Historia", "Wyloguj", "ala"]) {
      expect(within(bar).queryByText(gone)).not.toBeInTheDocument();
    }
  });

  it("bez gospodarstwa w profilu tytułem jest „Czat”", () => {
    renderMain({}, { ...profile, household: null });
    expect(within(screen.getByRole("banner")).getByRole("button", { name: "Czat" })).toBeInTheDocument();
  });
});

describe("opcje czatu", () => {
  it("tytuł czatu otwiera opcje, a Escape je zamyka i oddaje fokus tytułowi", async () => {
    renderMain();
    const title = screen.getByRole("button", { name: "Dom" });

    await userEvent.click(title);
    const dialog = screen.getByRole("dialog", { name: "Dom" });
    expect(title).toHaveAttribute("aria-expanded", "true");
    expect(within(dialog).getByRole("link", { name: "Gospodarstwo i domownicy" })).toHaveAttribute(
      "href",
      "/household",
    );

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(title).toHaveFocus();
  });

  it("link do dawnych rozmów tylko przy niepustym archiwum (#78)", async () => {
    renderMain({ "GET /api/chat/archive": [message] });
    await userEvent.click(screen.getByRole("button", { name: "Dom" }));

    expect(await screen.findByRole("link", { name: "Moje dawne rozmowy" })).toHaveAttribute(
      "href",
      "/chat-archive",
    );
  });

  it("bez archiwum nie ma linku do dawnych rozmów", async () => {
    const fetch = renderMain();
    await userEvent.click(screen.getByRole("button", { name: "Dom" }));

    await vi.waitFor(() =>
      expect(fetch.mock.calls.some(([url]) => url === "/api/chat/archive")).toBe(true),
    );
    expect(screen.queryByRole("link", { name: "Moje dawne rozmowy" })).not.toBeInTheDocument();
  });

  it("„Zamknij” zamyka opcje", async () => {
    renderMain();
    await userEvent.click(screen.getByRole("button", { name: "Dom" }));
    await userEvent.click(screen.getByRole("button", { name: "Zamknij" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("po potwierdzeniu ukrywa historię czatu u siebie", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetch = renderMain({ "DELETE /api/chat/messages": () => jsonResponse(null, 204) });
    expect(await screen.findByText("stara wiadomość")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Dom" }));
    await userEvent.click(screen.getByRole("button", { name: "Ukryj historię u siebie" }));

    await waitFor(() => expect(screen.queryByText("stara wiadomość")).not.toBeInTheDocument());
    // Czat jest wspólny (#78) — potwierdzenie mówi, że domownicy nadal widzą wiadomości.
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("Domownicy nadal je zobaczą"));
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat/messages",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("bez potwierdzenia historia zostaje", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetch = renderMain();
    await screen.findByText("stara wiadomość");

    await userEvent.click(screen.getByRole("button", { name: "Dom" }));
    await userEvent.click(screen.getByRole("button", { name: "Ukryj historię u siebie" }));

    expect(screen.getByText("stara wiadomość")).toBeInTheDocument();
    expect(fetch.mock.calls.every(([, init]) => init?.method !== "DELETE")).toBe(true);
  });

  it("przy pustej historii nie ma czego ukrywać", async () => {
    renderMain({ "GET /api/chat/messages": [] });
    await screen.findByText(/Napisz, czego potrzebujesz/);

    await userEvent.click(screen.getByRole("button", { name: "Dom" }));
    expect(screen.getByRole("button", { name: "Ukryj historię u siebie" })).toBeDisabled();
  });
});
