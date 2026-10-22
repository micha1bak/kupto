import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DISMISS_KEY, captureInstallPrompt, clearInstallPrompt } from "../pwa/install";
import { InstallBanner } from "./InstallBanner";

const IPHONE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";

const target = new EventTarget();
captureInstallPrompt(target as unknown as Window);

function firePrompt(outcome: "accepted" | "dismissed") {
  const event = Object.assign(new Event("beforeinstallprompt", { cancelable: true }), {
    prompt: vi.fn().mockResolvedValue(undefined),
    userChoice: Promise.resolve({ outcome, platform: "web" }),
  });
  act(() => {
    target.dispatchEvent(event);
  });
  return event;
}

function mockIphone() {
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue(IPHONE_UA);
}

function mockStandalone() {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({ matches: query === "(display-mode: standalone)" }) as MediaQueryList,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  act(() => clearInstallPrompt());
});

describe("InstallBanner", () => {
  it("bez możliwości instalacji (np. desktop) nic nie pokazuje", () => {
    const { container } = render(<InstallBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("na Androidzie przycisk „Zainstaluj” otwiera okno instalacji, a akceptacja chowa baner", async () => {
    render(<InstallBanner />);
    const event = firePrompt("accepted");
    await userEvent.click(screen.getByRole("button", { name: "Zainstaluj" }));
    expect(event.prompt).toHaveBeenCalled();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(localStorage.getItem(DISMISS_KEY)).toBeNull();
  });

  it("odrzucenie w oknie instalacji zapamiętuje zamknięcie", async () => {
    render(<InstallBanner />);
    firePrompt("dismissed");
    await userEvent.click(screen.getByRole("button", { name: "Zainstaluj" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(localStorage.getItem(DISMISS_KEY)).not.toBeNull();
  });

  it("na iPhonie pokazuje instrukcję i informację o powiadomieniach", () => {
    mockIphone();
    render(<InstallBanner />);
    const banner = screen.getByRole("complementary", { name: "Instalacja aplikacji" });
    expect(banner).toHaveTextContent("Udostępnij");
    expect(banner).toHaveTextContent("„Do ekranu początkowego”");
    expect(banner).toHaveTextContent(/powiadomienia/);
    expect(screen.queryByRole("button", { name: "Zainstaluj" })).not.toBeInTheDocument();
  });

  it("„×” zamyka baner i zapamiętuje to na kolejne otwarcia", async () => {
    mockIphone();
    const { unmount } = render(<InstallBanner />);
    await userEvent.click(screen.getByRole("button", { name: "Zamknij" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    unmount();
    render(<InstallBanner />);
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("w zainstalowanej aplikacji (standalone) się nie pokazuje", () => {
    mockIphone();
    mockStandalone();
    render(<InstallBanner />);
    firePrompt("accepted");
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });
});
