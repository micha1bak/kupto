import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecipesPage, parseAmount } from "./RecipesPage";
import { addedMessage, ingredientLabel } from "./IngredientsToList";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import type { Recipe } from "../api/types";

afterEach(() => vi.unstubAllGlobals());

const pancakes: Recipe = {
  id: 5,
  name: "Naleśniki",
  servings: "10 sztuk",
  source_url: "https://przepisy.example/nalesniki",
  instructions: "Zmiksuj i smaż.",
  ingredients: [
    { id: 11, name: "mąka pszenna", amount: null, unit: null, note: "2 szklanki", category: null },
    { id: 12, name: "mleko", amount: 0.5, unit: "l", note: null, category: "Nabiał" },
    { id: 13, name: "jajka", amount: 2, unit: "szt", note: null, category: "Nabiał" },
  ],
  created_by: "ola",
  created_at: "2026-10-22T10:00:00Z",
  updated_at: "2026-10-22T10:00:00Z",
};

function body(fetchMock: ReturnType<typeof mockFetch>, key: string) {
  const call = fetchMock.mock.calls.find(([url, init]) => `${init?.method ?? "GET"} ${url}` === key);
  return JSON.parse(String(call![1]!.body));
}

test("formatowanie składników i komunikatu", () => {
  expect(ingredientLabel(pancakes.ingredients[0])).toBe("mąka pszenna — 2 szklanki");
  expect(ingredientLabel(pancakes.ingredients[1])).toBe("mleko — 0,5 l");
  expect(ingredientLabel({ ...pancakes.ingredients[2], amount: null, unit: null })).toBe("jajka");
  expect(
    addedMessage({
      added: [
        { name: "mleko", category: "Nabiał", already_on_list: true },
        { name: "jajka", category: "Nabiał", already_on_list: false },
      ],
    }),
  ).toBe("Dodano na listę: mleko (już było na liście), jajka.");
  expect(parseAmount("0,5")).toBe(0.5);
  expect(parseAmount(" ")).toBeNull();
  expect(parseAmount("dużo")).toBeNull();
  expect(parseAmount("0")).toBeNull();
});

test("lista przepisów gospodarstwa", async () => {
  mockFetch({
    "GET /api/recipes": [
      { id: 5, name: "Naleśniki", servings: "10 sztuk", ingredient_count: 3, updated_at: "" },
      { id: 6, name: "Pierogi", servings: null, ingredient_count: 5, updated_at: "" },
    ],
  });

  renderWithProviders(<RecipesPage />, { route: "/recipes" });

  const list = await screen.findByRole("list", { name: "Przepisy" });
  const links = within(list).getAllByRole("link");
  expect(links.map((l) => l.textContent)).toEqual(["Naleśniki", "Pierogi"]);
  expect(links[0]).toHaveAttribute("href", "/recipes/5");
  expect(within(list).getByText("10 sztuk · składniki: 3")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Nowy przepis" })).toHaveAttribute("href", "/recipes/new");
  expect(screen.getByRole("link", { name: "Plan obiadów" })).toHaveAttribute("href", "/meal-plan");
});

test("pusta baza przepisów podpowiada zapis przez czat", async () => {
  mockFetch({ "GET /api/recipes": [] });

  renderWithProviders(<RecipesPage />, { route: "/recipes" });

  expect(await screen.findByText(/zapisz ten przepis/)).toBeInTheDocument();
});

test("zaznaczone składniki trafiają na listę w kolejności przepisu", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({
    "GET /api/recipes/5": pancakes,
    "POST /api/recipes/5/to-list": {
      added: [
        { name: "mąka pszenna", category: "Produkty suche", already_on_list: false },
        { name: "mleko", category: "Nabiał", already_on_list: true },
      ],
    },
  });

  renderWithProviders(<RecipesPage />, { route: "/recipes/5" });

  const add = await screen.findByRole("button", { name: "Dodaj zaznaczone na listę" });
  expect(add).toBeDisabled();
  expect(screen.getByText("Zmiksuj i smaż.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "źródło" })).toHaveAttribute(
    "href",
    "https://przepisy.example/nalesniki",
  );
  await user.click(screen.getByRole("checkbox", { name: "mleko — 0,5 l" }));
  await user.click(screen.getByRole("checkbox", { name: "mąka pszenna — 2 szklanki" }));
  await user.click(add);

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Dodano na listę: mąka pszenna, mleko (już było na liście).",
  );
  expect(body(fetchMock, "POST /api/recipes/5/to-list")).toEqual({ ingredient_ids: [11, 12] });
  // Po dodaniu zaznaczenie znika.
  expect(screen.getByRole("checkbox", { name: "mleko — 0,5 l" })).not.toBeChecked();
});

test("nowy przepis z formularza", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({
    "POST /api/recipes": () => jsonResponse(pancakes, 201),
    "GET /api/recipes/5": pancakes,
  });

  renderWithProviders(<RecipesPage />, { route: "/recipes/new" });

  await user.type(screen.getByLabelText("Nazwa"), " Naleśniki ");
  await user.type(screen.getByLabelText("Składnik 1"), "mleko");
  await user.type(screen.getByLabelText("Ilość 1"), "0,5");
  await user.selectOptions(screen.getByLabelText("Jednostka 1"), "l");
  await user.type(screen.getByLabelText("Składnik 2"), "mąka");
  await user.type(screen.getByLabelText("Notatka 2"), "2 szklanki");
  await user.click(screen.getByRole("button", { name: "Usuń składnik 3" }));
  await user.click(screen.getByRole("button", { name: "Zapisz przepis" }));

  // Po zapisie widok szczegółów nowego przepisu.
  expect(await screen.findByRole("heading", { name: "Naleśniki" })).toBeInTheDocument();
  expect(body(fetchMock, "POST /api/recipes")).toEqual({
    name: "Naleśniki",
    servings: null,
    source_url: null,
    instructions: null,
    ingredients: [
      { name: "mleko", amount: 0.5, unit: "l", note: null, category: null },
      { name: "mąka", amount: null, unit: null, note: "2 szklanki", category: null },
    ],
  });
});

test("przepis bez składników nie jest wysyłany", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({});

  renderWithProviders(<RecipesPage />, { route: "/recipes/new" });

  await user.type(screen.getByLabelText("Nazwa"), "Bigos");
  await user.click(screen.getByRole("button", { name: "Zapisz przepis" }));

  expect(screen.getByText("Dodaj co najmniej jeden składnik.")).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("edycja zastępuje przepis i zachowuje kategorie składników", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({
    "GET /api/recipes/5": pancakes,
    "PUT /api/recipes/5": (_url: string, init: RequestInit) =>
      jsonResponse({ ...pancakes, ...JSON.parse(String(init.body)) }),
  });

  renderWithProviders(<RecipesPage />, { route: "/recipes/5/edit" });

  const name = await screen.findByLabelText("Nazwa");
  expect(name).toHaveValue("Naleśniki");
  expect(screen.getByLabelText("Ilość 2")).toHaveValue("0,5");
  await user.click(screen.getByRole("button", { name: "Usuń składnik 1" }));
  await user.click(screen.getByRole("button", { name: "Zapisz przepis" }));

  await waitFor(() => expect(fetchMock.mock.calls.some(([, i]) => i?.method === "PUT")).toBe(true));
  const sent = body(fetchMock, "PUT /api/recipes/5");
  expect(sent.ingredients).toEqual([
    { name: "mleko", amount: 0.5, unit: "l", note: null, category: "Nabiał" },
    { name: "jajka", amount: 2, unit: "szt", note: null, category: "Nabiał" },
  ]);
  expect(sent.servings).toBe("10 sztuk");
});

test("usunięcie przepisu po potwierdzeniu", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("confirm", vi.fn(() => true));
  const fetchMock = mockFetch({
    "GET /api/recipes/5": pancakes,
    "DELETE /api/recipes/5": () => jsonResponse(null, 204),
    "GET /api/recipes": [],
  });

  renderWithProviders(<RecipesPage />, { route: "/recipes/5" });

  await user.click(await screen.findByRole("button", { name: "Usuń przepis" }));

  expect(window.confirm).toHaveBeenCalledWith("Usunąć przepis „Naleśniki”?");
  expect(await screen.findByRole("heading", { name: "Nasze przepisy" })).toBeInTheDocument();
  const deleted = fetchMock.mock.calls.some(
    ([url, init]) => url === "/api/recipes/5" && init?.method === "DELETE",
  );
  expect(deleted).toBe(true);
});
