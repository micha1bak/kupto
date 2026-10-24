import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MealPlanPage } from "./MealPlanPage";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import type { MealPlanEntry, Recipe } from "../api/types";

// „Dziś” to wtorek 27 października 2026; fałszujemy tylko Date, by nie wstrzymywać userEvent.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 27, 12, 0));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const PLAN = "GET /api/meal-plan?from=2026-10-26&to=2026-11-08";

const pancakes: MealPlanEntry = {
  id: 1,
  day: "2026-10-28",
  name: "Naleśniki",
  recipe_id: 5,
  planned_by: "ala",
  updated_at: "2026-10-24T10:00:00Z",
};

const soup: MealPlanEntry = {
  id: 2,
  day: "2026-10-30",
  name: "Zupa pomidorowa",
  recipe_id: null,
  planned_by: "ola",
  updated_at: "2026-10-24T10:00:00Z",
};

const recipes = [
  { id: 5, name: "Naleśniki", servings: null, ingredient_count: 2, updated_at: "" },
  { id: 6, name: "Pierogi ruskie", servings: null, ingredient_count: 4, updated_at: "" },
];

function body(fetchMock: ReturnType<typeof mockFetch>, key: string) {
  const call = fetchMock.mock.calls.find(([url, init]) => `${init?.method ?? "GET"} ${url}` === key);
  return JSON.parse(String(call![1]!.body));
}

const calls = (fetchMock: ReturnType<typeof mockFetch>, key: string) =>
  fetchMock.mock.calls.filter(([url, init]) => `${init?.method ?? "GET"} ${url}` === key).length;

const day = (name: string) => screen.getByRole("listitem", { name });

test("dwa tygodnie od poniedziałku z daniami i linkiem do przepisu", async () => {
  mockFetch({ [PLAN]: [pancakes, soup] });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });

  const first = await screen.findByRole("region", { name: "Tydzień 26 paź – 1 lis" });
  const second = screen.getByRole("region", { name: "Tydzień 2 lis – 8 lis" });
  expect(within(first).getAllByRole("listitem")).toHaveLength(7);
  expect(within(second).getAllByRole("listitem")).toHaveLength(7);

  expect(within(day("wtorek 27 paź")).getByText(/dziś/)).toBeInTheDocument();
  expect(within(day("środa 28 paź")).getByRole("link", { name: "Naleśniki" })).toHaveAttribute(
    "href",
    "/recipes/5",
  );
  expect(within(day("środa 28 paź")).getByText("zaplanował(a) ala")).toBeInTheDocument();
  // Danie bez przepisu: bez linku i bez dodawania składników.
  const friday = day("piątek 30 paź");
  expect(within(friday).getByText("Zupa pomidorowa")).toBeInTheDocument();
  expect(within(friday).queryByRole("link")).not.toBeInTheDocument();
  expect(
    within(friday).queryByRole("button", { name: "Dodaj brakujące składniki" }),
  ).not.toBeInTheDocument();
  expect(within(day("poniedziałek 26 paź")).getByRole("button", { name: "Dodaj danie" })).toBeVisible();
});

test("nawigacja tygodniami", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({
    [PLAN]: [pancakes],
    "GET /api/meal-plan?from=2026-11-02&to=2026-11-15": [{ ...soup, day: "2026-11-03" }],
    "GET /api/meal-plan?from=2026-10-19&to=2026-11-01": [],
  });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });
  await screen.findByRole("region", { name: "Tydzień 26 paź – 1 lis" });
  expect(screen.queryByRole("button", { name: "Ten tydzień" })).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Później →" }));
  expect(await screen.findByRole("region", { name: "Tydzień 9 lis – 15 lis" })).toBeInTheDocument();
  expect(within(day("wtorek 3 lis")).getByText("Zupa pomidorowa")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Ten tydzień" }));
  expect(await screen.findByRole("link", { name: "Naleśniki" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "← Wcześniej" }));
  expect(await screen.findByRole("region", { name: "Tydzień 19 paź – 25 paź" })).toBeInTheDocument();
  expect(calls(fetchMock, "GET /api/meal-plan?from=2026-10-19&to=2026-11-01")).toBe(1);
});

test("dodanie dania z przepisu podpowiada nazwę", async () => {
  const user = userEvent.setup();
  let saved = false;
  const fetchMock = mockFetch({
    [PLAN]: () =>
      jsonResponse(
        saved
          ? [pancakes, { ...pancakes, id: 3, day: "2026-10-29", name: "Pierogi ruskie", recipe_id: 6 }]
          : [pancakes],
      ),
    "GET /api/recipes": recipes,
    "PUT /api/meal-plan/2026-10-29": () => {
      saved = true;
      return jsonResponse({});
    },
  });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });
  await screen.findByRole("link", { name: "Naleśniki" });
  await user.click(within(day("czwartek 29 paź")).getByRole("button", { name: "Dodaj danie" }));

  const form = screen.getByRole("form", { name: "Danie na czwartek 29 paź" });
  const select = within(form).getByLabelText("Przepis");
  await waitFor(() => expect(select).toBeEnabled());
  await user.selectOptions(select, "Pierogi ruskie");
  expect(within(form).getByLabelText("Danie")).toHaveValue("Pierogi ruskie");
  await user.click(within(form).getByRole("button", { name: "Zapisz" }));

  expect(
    await within(day("czwartek 29 paź")).findByRole("link", { name: "Pierogi ruskie" }),
  ).toHaveAttribute("href", "/recipes/6");
  expect(body(fetchMock, "PUT /api/meal-plan/2026-10-29")).toEqual({
    name: "Pierogi ruskie",
    recipe_id: 6,
  });
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
});

test("zmiana dania na własną nazwę bez przepisu", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch({
    [PLAN]: [pancakes],
    "GET /api/recipes": recipes,
    "PUT /api/meal-plan/2026-10-28": {},
  });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });
  await screen.findByRole("link", { name: "Naleśniki" });
  await user.click(within(day("środa 28 paź")).getByRole("button", { name: "Zmień" }));

  const form = screen.getByRole("form", { name: "Danie na środa 28 paź" });
  const select = within(form).getByLabelText("Przepis");
  await waitFor(() => expect(select).toHaveValue("5"));
  const name = within(form).getByLabelText("Danie");
  expect(name).toHaveValue("Naleśniki");

  // Bez nazwy i przepisu nic nie wysyłamy.
  await user.selectOptions(select, "— bez przepisu —");
  await user.clear(name);
  await user.click(within(form).getByRole("button", { name: "Zapisz" }));
  expect(within(form).getByText("Podaj nazwę dania albo wybierz przepis.")).toBeInTheDocument();

  // Własna nazwa nie jest nadpisywana przy wyborze przepisu.
  await user.type(name, "Zupa pomidorowa");
  await user.selectOptions(select, "Pierogi ruskie");
  expect(name).toHaveValue("Zupa pomidorowa");
  await user.selectOptions(select, "— bez przepisu —");
  await user.click(within(form).getByRole("button", { name: "Zapisz" }));

  await waitFor(() => expect(screen.queryByRole("form")).not.toBeInTheDocument());
  expect(body(fetchMock, "PUT /api/meal-plan/2026-10-28")).toEqual({
    name: "Zupa pomidorowa",
    recipe_id: null,
  });
  expect(calls(fetchMock, PLAN)).toBe(2);
});

test("usunięcie dania wymaga potwierdzenia", async () => {
  const user = userEvent.setup();
  let deleted = false;
  const confirm = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
  vi.stubGlobal("confirm", confirm);
  const fetchMock = mockFetch({
    [PLAN]: () => jsonResponse(deleted ? [] : [pancakes]),
    "DELETE /api/meal-plan/2026-10-28": () => {
      deleted = true;
      return jsonResponse(null, 204);
    },
  });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });
  await screen.findByRole("link", { name: "Naleśniki" });
  const wednesday = day("środa 28 paź");

  await user.click(within(wednesday).getByRole("button", { name: "Usuń" }));
  expect(confirm).toHaveBeenCalledWith("Usunąć „Naleśniki” z planu na środa 28 paź?");
  expect(calls(fetchMock, "DELETE /api/meal-plan/2026-10-28")).toBe(0);

  await user.click(within(wednesday).getByRole("button", { name: "Usuń" }));
  await waitFor(() =>
    expect(screen.queryByRole("link", { name: "Naleśniki" })).not.toBeInTheDocument(),
  );
  expect(calls(fetchMock, "DELETE /api/meal-plan/2026-10-28")).toBe(1);
  expect(within(day("środa 28 paź")).getByRole("button", { name: "Dodaj danie" })).toBeVisible();
});

test("brakujące składniki z dnia z przepisem trafiają na listę", async () => {
  const user = userEvent.setup();
  const recipe: Recipe = {
    id: 5,
    name: "Naleśniki",
    servings: null,
    source_url: null,
    instructions: null,
    ingredients: [
      { id: 11, name: "mąka pszenna", amount: null, unit: null, note: "2 szklanki", category: null },
      { id: 12, name: "mleko", amount: 0.5, unit: "l", note: null, category: "Nabiał" },
    ],
    created_by: "ola",
    created_at: "",
    updated_at: "",
  };
  const fetchMock = mockFetch({
    [PLAN]: [pancakes],
    "GET /api/recipes/5": recipe,
    "POST /api/recipes/5/to-list": {
      added: [{ name: "mleko", category: "Nabiał", already_on_list: false }],
    },
  });

  const { queryClient } = renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  await screen.findByRole("link", { name: "Naleśniki" });
  const wednesday = day("środa 28 paź");

  const toggle = within(wednesday).getByRole("button", { name: "Dodaj brakujące składniki" });
  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  await user.click(await within(wednesday).findByLabelText("mleko — 0,5 l"));
  await user.click(within(wednesday).getByRole("button", { name: "Dodaj zaznaczone na listę" }));

  expect(await within(wednesday).findByRole("status")).toHaveTextContent(
    "Dodano na listę: mleko.",
  );
  expect(body(fetchMock, "POST /api/recipes/5/to-list")).toEqual({ ingredient_ids: [12] });
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list"] });
});

test("błąd wczytania planu", async () => {
  mockFetch({ [PLAN]: () => jsonResponse({ detail: "Zakres planu może mieć najwyżej 62 dni." }, 400) });

  renderWithProviders(<MealPlanPage />, { route: "/meal-plan" });

  expect(await screen.findByText("Zakres planu może mieć najwyżej 62 dni.")).toBeInTheDocument();
});
