import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListView } from "./ListView";
import { LIST_POLL_MS } from "../api/queries";
import type { ShoppingList } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

const need = (id: number, user_id: number, login: string, amount: number | null, unit: string | null) => ({
  id,
  user_id,
  login,
  amount,
  unit,
  note: null,
  created_at: "2026-10-21T10:00:00Z",
});

const list: ShoppingList = {
  id: 1,
  groups: [
    {
      category: "Nabiał",
      items: [
        {
          id: 10,
          name: "mleko",
          category: "Nabiał",
          quantities: [{ amount: 3, unit: "l" }],
          needs: [need(1, 1, "ala", 1, "l"), need(2, 2, "ola", 2, "l")] as never,
          bought: false,
          bought_at: null,
          bought_by: null,
        },
      ],
    },
    {
      category: "Chemia i higiena",
      items: [
        {
          id: 11,
          name: "płyn do naczyń",
          category: "Chemia i higiena",
          quantities: [],
          needs: [need(3, 2, "ola", null, null)] as never,
          bought: false,
          bought_at: null,
          bought_by: null,
        },
      ],
    },
  ],
};

test("renders items grouped by category with quantities and requesters", async () => {
  mockFetch({ "GET /api/list": list });
  renderWithProviders(<ListView userId={1} />);

  const dairy = await screen.findByRole("list", { name: "Nabiał" });
  expect(within(dairy).getByText("mleko")).toBeInTheDocument();
  expect(within(dairy).getByText("3 l")).toBeInTheDocument();
  expect(within(dairy).getByText(/ola: 2 l/)).toBeInTheDocument();
  expect(screen.getByRole("list", { name: "Chemia i higiena" })).toBeInTheDocument();
  // wycofać można tylko własne zapotrzebowanie
  expect(screen.getAllByRole("button", { name: /Wycofaj moje/ })).toHaveLength(1);
});

test("checking an item is optimistic", async () => {
  let resolve: (r: Response) => void = () => {};
  mockFetch({
    "GET /api/list": list,
    "POST /api/list/items/10/bought": () => new Promise<Response>((r) => (resolve = r)),
  });
  renderWithProviders(<ListView userId={1} />);

  const checkbox = await screen.findByRole("checkbox", { name: "Kupione: mleko" });
  await userEvent.click(checkbox);

  expect(checkbox).toBeChecked();
  expect(screen.getByRole("button", { name: "Zakończ zakupy" })).toBeInTheDocument();
  resolve(jsonResponse(list));
});

test("reverts optimistic check when the request fails", async () => {
  mockFetch({
    "GET /api/list": list,
    "POST /api/list/items/10/bought": () => jsonResponse({ detail: "Błąd" }, 500),
  });
  renderWithProviders(<ListView userId={1} />);

  const checkbox = await screen.findByRole("checkbox", { name: "Kupione: mleko" });
  await userEvent.click(checkbox);

  await vi.waitFor(() => expect(checkbox).not.toBeChecked());
});

test("manual add sends parsed amount and optional fields", async () => {
  const fetch = mockFetch({
    "GET /api/list": list,
    "POST /api/list/needs": () => jsonResponse(list, 201),
  });
  renderWithProviders(<ListView userId={1} />);

  await userEvent.type(await screen.findByLabelText("Produkt"), "jabłka");
  await userEvent.type(screen.getByLabelText("Ilość"), "1,5");
  await userEvent.selectOptions(screen.getByLabelText("Jednostka"), "kg");
  await userEvent.click(screen.getByRole("button", { name: "Dodaj" }));

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(JSON.parse(fetch.mock.calls[1][1]!.body as string)).toEqual({
    name: "jabłka",
    amount: 1.5,
    unit: "kg",
    category: null,
  });
});

test("list is polled often enough to show others' changes within 10 seconds", () => {
  expect(LIST_POLL_MS).toBeLessThanOrEqual(10_000);
});
