import { screen } from "@testing-library/react";
import { ChatArchivePage } from "./ChatArchivePage";
import { mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

test("shows the old private conversation read-only (#78)", async () => {
  mockFetch({
    "GET /api/chat/archive": [
      { id: 1, role: "user", content: "kup mleko", created_at: "", author: { id: 1, name: "Ala" }, mine: true },
      { id: 2, role: "assistant", content: "Dodałem mleko.", created_at: "", author: null, mine: false },
    ],
  });
  renderWithProviders(<ChatArchivePage />, { route: "/chat-archive" });

  expect(screen.getByRole("heading", { name: "Moje dawne rozmowy" })).toBeInTheDocument();
  expect((await screen.findByText("kup mleko")).parentElement).toHaveTextContent("Ty");
  expect(screen.getByText("Dodałem mleko.").parentElement).toHaveTextContent("Asystent");
  // Tylko odczyt — bez pola wiadomości.
  expect(screen.queryByLabelText("Wiadomość")).not.toBeInTheDocument();
});
