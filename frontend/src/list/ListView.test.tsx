import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ListView } from "./ListView";
import { LIST_FALLBACK_POLL_MS } from "../api/queries";
import type { ShoppingList } from "../api/types";
import { FakeEventSource } from "../test/fakeEventSource";
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
      pinned: false,
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
      pinned: false,
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
  shoppers: [],
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

test("without the live stream the list is polled often enough to show changes within 30 seconds", () => {
  expect(LIST_FALLBACK_POLL_MS).toBeLessThanOrEqual(30_000);
});

const pinnedList: ShoppingList = {
  ...list,
  groups: [{ ...list.groups[1], pinned: true }, list.groups[0]],
};

/** jsdom nie liczy układu — każda grupa dostaje własny pas 100 px w kolejności w DOM. */
function mockGroupLayout() {
  return vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    const group = this.closest(".group");
    const index = group ? [...group.parentElement!.children].filter((c) => c.matches(".group")).indexOf(group) : 0;
    return new DOMRect(0, index * 100, 300, 100);
  });
}

const groupNames = () => screen.getAllByRole("list", { name: /./ }).map((l) => l.getAttribute("aria-label"));

test("renders groups in the order from the API and marks pinned ones", async () => {
  mockFetch({ "GET /api/list": pinnedList });
  renderWithProviders(<ListView userId={1} />);

  await screen.findByRole("list", { name: "Nabiał" });
  expect(groupNames()).toEqual(["Chemia i higiena", "Nabiał"]);
  expect(screen.getAllByRole("img", { name: "przypięta" })).toHaveLength(1);
  expect(screen.getByRole("button", { name: "Odepnij kategorię Chemia i higiena" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Odepnij kategorię Nabiał" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Przywróć kolejność" })).toBeInTheDocument();
});

test("without pins there is nothing to unpin or reset", async () => {
  mockFetch({ "GET /api/list": list });
  renderWithProviders(<ListView userId={1} />);

  await screen.findByRole("list", { name: "Nabiał" });
  expect(screen.queryByRole("button", { name: /Odepnij/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Przywróć kolejność" })).not.toBeInTheDocument();
});

test("unpinning a category shows the list from the response", async () => {
  const fetch = mockFetch({
    "GET /api/list": pinnedList,
    "DELETE /api/list/category-order/Chemia%20i%20higiena": list,
  });
  renderWithProviders(<ListView userId={1} />);

  await userEvent.click(await screen.findByRole("button", { name: "Odepnij kategorię Chemia i higiena" }));

  await vi.waitFor(() => expect(groupNames()).toEqual(["Nabiał", "Chemia i higiena"]));
  expect(fetch).toHaveBeenCalledWith("/api/list/category-order/Chemia%20i%20higiena", expect.anything());
  expect(screen.queryByRole("img", { name: "przypięta" })).not.toBeInTheDocument();
});

test("restoring the automatic order asks for confirmation", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  const fetch = mockFetch({ "GET /api/list": pinnedList, "DELETE /api/list/category-order": list });
  renderWithProviders(<ListView userId={1} />);

  const reset = await screen.findByRole("button", { name: "Przywróć kolejność" });
  await userEvent.click(reset);
  expect(fetch).toHaveBeenCalledTimes(1);

  await userEvent.click(reset);
  await vi.waitFor(() => expect(groupNames()).toEqual(["Nabiał", "Chemia i higiena"]));
  expect(fetch).toHaveBeenLastCalledWith("/api/list/category-order", expect.objectContaining({ method: "DELETE" }));
  confirm.mockRestore();
});

test("moving a category header with the keyboard pins it optimistically", async () => {
  const rect = mockGroupLayout();
  let resolve: (r: Response) => void = () => {};
  const fetch = mockFetch({
    "GET /api/list": list,
    "PUT /api/list/category-order/Chemia%20i%20higiena": () => new Promise<Response>((r) => (resolve = r)),
  });
  renderWithProviders(<ListView userId={1} />);

  const handle = await screen.findByRole("button", { name: "Chemia i higiena" });
  handle.focus();
  await userEvent.keyboard("[Space]");
  await userEvent.keyboard("[ArrowUp]");
  await userEvent.keyboard("[Space]");

  await vi.waitFor(() => expect(groupNames()).toEqual(["Chemia i higiena", "Nabiał"]));
  const [, init] = fetch.mock.calls.find(([url]) => url.startsWith("/api/list/category-order/"))!;
  expect(init).toMatchObject({ method: "PUT" });
  expect(JSON.parse(init!.body as string)).toEqual({ after: null, before: "Nabiał" });
  expect(screen.getByRole("img", { name: "przypięta" })).toBeInTheDocument();
  resolve(jsonResponse(pinnedList));
  rect.mockRestore();
});

test("a failed pin restores the previous order", async () => {
  const rect = mockGroupLayout();
  mockFetch({
    "GET /api/list": list,
    "PUT /api/list/category-order/Nabia%C5%82": () => jsonResponse({ detail: "Błąd zapisu." }, 500),
  });
  renderWithProviders(<ListView userId={1} />);

  const handle = await screen.findByRole("button", { name: "Nabiał" });
  handle.focus();
  await userEvent.keyboard("[Space]");
  await userEvent.keyboard("[ArrowDown]");
  await userEvent.keyboard("[Space]");

  expect(await screen.findByText("Błąd zapisu.")).toBeInTheDocument();
  expect(groupNames()).toEqual(["Nabiał", "Chemia i higiena"]);
  rect.mockRestore();
});

const shopper = (user_id: number, login: string) => ({
  user_id,
  login,
  since: "2026-10-22T12:05:00Z",
  expires_at: "2026-10-22T15:05:00Z",
});

test("going shopping sends the status and shows it from the response", async () => {
  const fetch = mockFetch({
    "GET /api/list": list,
    "POST /api/list/shopping": { ...list, shoppers: [shopper(1, "ala")] },
  });
  renderWithProviders(<ListView userId={1} />);

  await userEvent.click(await screen.findByRole("button", { name: "Idę na zakupy" }));

  const banner = await screen.findByRole("list", { name: "Kto robi zakupy" });
  expect(banner).toHaveTextContent(/Robisz zakupy od \d{2}:\d{2}/);
  expect(fetch).toHaveBeenLastCalledWith("/api/list/shopping", expect.objectContaining({ method: "POST" }));
  expect(screen.queryByRole("button", { name: "Idę na zakupy" })).not.toBeInTheDocument();
});

test("household members see who is shopping", async () => {
  mockFetch({ "GET /api/list": { ...list, shoppers: [shopper(2, "ania")] } });
  renderWithProviders(<ListView userId={1} />);

  const banner = await screen.findByRole("list", { name: "Kto robi zakupy" });
  expect(banner).toHaveTextContent(/ania robi zakupy od \d{2}:\d{2}/);
  // Cudzy status nie zmienia mojego przycisku.
  expect(screen.getByRole("button", { name: "Idę na zakupy" })).toBeInTheDocument();
});

test("finishing my shopping status removes it", async () => {
  const fetch = mockFetch({
    "GET /api/list": { ...list, shoppers: [shopper(1, "ala"), shopper(2, "ania")] },
    "DELETE /api/list/shopping": { ...list, shoppers: [shopper(2, "ania")] },
  });
  renderWithProviders(<ListView userId={1} />);

  await userEvent.click(await screen.findByRole("button", { name: "Kończę" }));

  await screen.findByRole("button", { name: "Idę na zakupy" });
  expect(screen.getByRole("list", { name: "Kto robi zakupy" })).not.toHaveTextContent("Robisz zakupy");
  expect(fetch).toHaveBeenLastCalledWith("/api/list/shopping", expect.objectContaining({ method: "DELETE" }));
});

test("without shoppers there is no shopping banner", async () => {
  mockFetch({ "GET /api/list": { id: 1, groups: [] } });
  renderWithProviders(<ListView userId={1} />);

  await screen.findByRole("button", { name: "Idę na zakupy" });
  expect(screen.queryByRole("list", { name: "Kto robi zakupy" })).not.toBeInTheDocument();
});

test("refetches the list when the live stream signals a change", async () => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  const fetch = mockFetch({ "GET /api/list": list });
  renderWithProviders(<ListView userId={1} />);
  await screen.findByText("mleko");
  expect(fetch).toHaveBeenCalledTimes(1);

  act(() => FakeEventSource.last.emit("ready"));
  act(() => FakeEventSource.last.emit("list_changed"));

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
});
