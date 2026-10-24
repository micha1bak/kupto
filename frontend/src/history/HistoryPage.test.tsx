import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HistoryPage, itemCount } from "./HistoryPage";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import type { ShoppingTrip } from "../api/types";

afterEach(() => vi.unstubAllGlobals());

function trip(id: number, finishedBy: string, items: [string, string][]): ShoppingTrip {
  const categories = [...new Set(items.map(([, category]) => category))];
  return {
    id,
    finished_at: "2026-10-21T16:30:00Z",
    finished_by: finishedBy,
    item_count: items.length,
    groups: categories.map((category) => ({
      category: category as ShoppingTrip["groups"][number]["category"],
      items: items
        .filter(([, c]) => c === category)
        .map(([name], index) => ({
          id: id * 100 + index,
          name,
          category: category as ShoppingTrip["groups"][number]["category"],
          quantities: [],
          needs: [],
          bought_at: "2026-10-21T16:00:00Z",
          bought_by: finishedBy,
        })),
    })),
  };
}

const milkTrip: ShoppingTrip = {
  id: 7,
  finished_at: "2026-10-21T16:30:00Z",
  finished_by: "ala",
  item_count: 2,
  groups: [
    {
      category: "Pieczywo",
      items: [
        {
          id: 1,
          name: "chleb",
          category: "Pieczywo",
          quantities: [],
          needs: [
            {
              user_id: 1,
              name: "ala",
              amount: null,
              unit: null,
              note: null,
              requested_at: "2026-10-20T08:00:00Z",
            },
          ],
          bought_at: "2026-10-21T16:10:00Z",
          bought_by: "ala",
        },
      ],
    },
    {
      category: "Nabiał",
      items: [
        {
          id: 2,
          name: "mleko",
          category: "Nabiał",
          quantities: [{ amount: 3, unit: "l" }],
          needs: [
            {
              user_id: 1,
              name: "ala",
              amount: 2,
              unit: "l",
              note: "bez laktozy",
              requested_at: "2026-10-20T08:00:00Z",
            },
            {
              user_id: 2,
              name: "ola",
              amount: 1,
              unit: "l",
              note: null,
              requested_at: "2026-10-20T09:00:00Z",
            },
          ],
          bought_at: "2026-10-21T16:05:00Z",
          bought_by: "ola",
        },
      ],
    },
  ],
};

test("shows trips with date, person and items grouped by category", async () => {
  mockFetch({ "GET /api/history": { trips: [milkTrip], next_cursor: null } });
  renderWithProviders(<HistoryPage />);

  const section = await screen.findByRole("region", { name: /21 paź 2026/ });
  expect(within(section).getByText(/zakończył\(a\) ala · 2 pozycje/)).toBeInTheDocument();
  const headings = within(section).getAllByRole("heading", { level: 4 });
  expect(headings.map((h) => h.textContent)).toEqual(["Pieczywo", "Nabiał"]);
  expect(within(section).getByText("mleko")).toBeInTheDocument();
  expect(within(section).getByText("3 l")).toBeInTheDocument();
  expect(
    within(section).getByText(/kupił\(a\) ola .* zgłaszali: ala \(2 l, „bez laktozy”\), ola \(1 l\)/),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Pokaż więcej" })).not.toBeInTheDocument();
});

test("loads older trips with show more", async () => {
  const fetch = mockFetch({
    "GET /api/history": { trips: [trip(9, "ola", [["kawa", "Napoje"]])], next_cursor: 9 },
    "GET /api/history?before=9": {
      trips: [trip(4, "ala", [["chleb", "Pieczywo"]])],
      next_cursor: null,
    },
  });
  renderWithProviders(<HistoryPage />);

  await screen.findByText("kawa");
  await userEvent.click(screen.getByRole("button", { name: "Pokaż więcej" }));

  expect(await screen.findByText("chleb")).toBeInTheDocument();
  expect(screen.getByText("kawa")).toBeInTheDocument();
  expect(screen.getAllByRole("region")).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Pokaż więcej" })).not.toBeInTheDocument();
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    "/api/history",
    "/api/history?before=9",
  ]);
});

test("failed show more keeps loaded trips", async () => {
  mockFetch({
    "GET /api/history": { trips: [trip(9, "ola", [["kawa", "Napoje"]])], next_cursor: 9 },
    "GET /api/history?before=9": () => jsonResponse({ detail: "Błąd serwera." }, 500),
  });
  renderWithProviders(<HistoryPage />);

  await screen.findByText("kawa");
  await userEvent.click(screen.getByRole("button", { name: "Pokaż więcej" }));

  expect(await screen.findByText("Błąd serwera.")).toBeInTheDocument();
  expect(screen.getByText("kawa")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Pokaż więcej" })).toBeEnabled();
});

test("empty history shows a hint", async () => {
  mockFetch({ "GET /api/history": { trips: [], next_cursor: null } });
  renderWithProviders(<HistoryPage />);

  expect(await screen.findByText("Nie ma jeszcze zakończonych zakupów.")).toBeInTheDocument();
});

test("history error is shown", async () => {
  mockFetch({ "GET /api/history": () => jsonResponse({ detail: "Błąd serwera." }, 500) });
  renderWithProviders(<HistoryPage />);

  expect(await screen.findByText("Błąd serwera.")).toBeInTheDocument();
});

test("search shows when and who last bought a product", async () => {
  const fetch = mockFetch({
    "GET /api/history": { trips: [milkTrip], next_cursor: null },
    "GET /api/history/products?q=%C5%BC%C3%B3%C5%82ty": [
      {
        name: "żółty ser",
        category: "Nabiał",
        last_bought_at: "2026-10-21T16:05:00Z",
        last_bought_by: "ola",
        last_trip_id: 7,
        last_quantities: [{ amount: 200, unit: "g" }],
        times_bought: 3,
      },
    ],
  });
  renderWithProviders(<HistoryPage />);
  await screen.findByText("mleko");

  await userEvent.type(screen.getByLabelText("Szukaj produktu w historii"), " żółty ");

  const results = await screen.findByRole("list", { name: "Wyniki wyszukiwania" });
  expect(within(results).getByText("żółty ser")).toBeInTheDocument();
  expect(
    within(results).getByText(/ostatnio 21 paź 2026, kupił\(a\) ola \(200 g\) · razem 3×/),
  ).toBeInTheDocument();
  expect(screen.queryByText("mleko")).not.toBeInTheDocument();
  // Opóźnienie: jedno zapytanie po skończeniu pisania, nie po każdym znaku.
  expect(fetch.mock.calls.filter(([url]) => url.startsWith("/api/history/products"))).toHaveLength(
    1,
  );

  await userEvent.clear(screen.getByLabelText("Szukaj produktu w historii"));
  expect(await screen.findByText("mleko")).toBeInTheDocument();
});

test("search without results", async () => {
  mockFetch({
    "GET /api/history": { trips: [], next_cursor: null },
    "GET /api/history/products?q=kawior": [],
  });
  renderWithProviders(<HistoryPage />);

  await userEvent.type(screen.getByLabelText("Szukaj produktu w historii"), "kawior");

  expect(await screen.findByText("Nikt jeszcze nie kupował „kawior”.")).toBeInTheDocument();
});

test("item count uses Polish plural forms", () => {
  expect([1, 2, 4, 5, 12, 14, 22, 25].map(itemCount)).toEqual([
    "1 pozycja",
    "2 pozycje",
    "4 pozycje",
    "5 pozycji",
    "12 pozycji",
    "14 pozycji",
    "22 pozycje",
    "25 pozycji",
  ]);
});
