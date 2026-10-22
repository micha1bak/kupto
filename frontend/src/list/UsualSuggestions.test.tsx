import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HIDDEN_ON_KEY, MAX_SHOWN, UsualSuggestions, today } from "./UsualSuggestions";
import { keys } from "../api/queries";
import type { Item, ShoppingList, UsualProduct } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

const product = (name: string, amount: number | null = null, unit: UsualProduct["unit"] = null): UsualProduct => ({
  name,
  category: "Nabiał",
  amount,
  unit,
  times_bought: 4,
  typical_interval_days: 7,
  last_bought_at: "2026-10-15T10:00:00Z",
  overdue: 1,
});

const item = (id: number, name: string): Item =>
  ({
    id,
    name,
    category: "Nabiał",
    quantities: [],
    needs: [],
    bought: false,
    bought_at: null,
    bought_by: null,
  }) as Item;

const listWith = (...names: string[]): ShoppingList => ({
  id: 1,
  groups: names.length ? [{ category: "Nabiał", pinned: false, items: names.map((n, i) => item(i + 1, n)) }] : [],
  shoppers: [],
});

test("shows usual products missing from the list", async () => {
  mockFetch({ "GET /api/history/usual": [product("mleko", 2, "l"), product("Chleb"), product("masło")] });
  renderWithProviders(<UsualSuggestions list={listWith("chleb")} />);

  expect(await screen.findByText("Zwykle kupujecie:")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Dodaj mleko (2 l)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Dodaj masło" })).toBeInTheDocument();
  // chleb jest już na liście (bez względu na wielkość liter)
  expect(screen.queryByRole("button", { name: /Dodaj chleb/i })).not.toBeInTheDocument();
});

test("shows at most a few products", async () => {
  const many = Array.from({ length: MAX_SHOWN + 3 }, (_, i) => product(`produkt ${i}`));
  mockFetch({ "GET /api/history/usual": many });
  renderWithProviders(<UsualSuggestions list={listWith()} />);

  await screen.findByText("Zwykle kupujecie:");
  expect(screen.getAllByRole("button", { name: /^Dodaj/ })).toHaveLength(MAX_SHOWN);
});

test("renders nothing without suggestions", async () => {
  const fetch = mockFetch({ "GET /api/history/usual": [] });
  const { container } = renderWithProviders(<UsualSuggestions list={listWith()} />);

  await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

test("one click adds a need with the typical amount", async () => {
  const updated = listWith("mleko");
  const fetch = mockFetch({
    "GET /api/history/usual": [product("mleko", 2, "l"), product("masło")],
    "POST /api/list/needs": () => jsonResponse(updated, 201),
  });
  const { queryClient } = renderWithProviders(<UsualSuggestions list={listWith()} />);

  await userEvent.click(await screen.findByRole("button", { name: "Dodaj mleko (2 l)" }));

  const [, init] = fetch.mock.calls.find(([url]) => url === "/api/list/needs")!;
  expect(init?.method).toBe("POST");
  expect(JSON.parse(init?.body as string)).toEqual({ name: "mleko", amount: 2, unit: "l", category: "Nabiał" });
  await vi.waitFor(() => expect(queryClient.getQueryData(keys.list)).toEqual(updated));
});

test("can be hidden for the rest of the day", async () => {
  mockFetch({ "GET /api/history/usual": [product("mleko")] });
  const first = renderWithProviders(<UsualSuggestions list={listWith()} />);

  await userEvent.click(await screen.findByRole("button", { name: "Ukryj na dziś" }));

  expect(screen.queryByText("Zwykle kupujecie:")).not.toBeInTheDocument();
  expect(localStorage.getItem(HIDDEN_ON_KEY)).toBe(today());
  first.unmount();

  // Po ponownym otwarciu tego samego dnia nadal ukryte…
  const second = renderWithProviders(<UsualSuggestions list={listWith()} />);
  await new Promise((r) => setTimeout(r, 20));
  expect(screen.queryByText("Zwykle kupujecie:")).not.toBeInTheDocument();
  second.unmount();

  // …a następnego dnia (inna zapisana data) podpowiedź wraca.
  localStorage.setItem(HIDDEN_ON_KEY, "2000-01-01");
  renderWithProviders(<UsualSuggestions list={listWith()} />);
  expect(await screen.findByText("Zwykle kupujecie:")).toBeInTheDocument();
});

test("today is the local calendar date", () => {
  expect(today(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
});
