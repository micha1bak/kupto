import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HouseholdPreferences } from "./HouseholdPreferences";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";
import type { HouseholdPreferences as Preferences } from "../api/types";

afterEach(() => vi.unstubAllGlobals());

const URL = "/api/households/me/preferences";

const empty: Preferences = {
  people: null,
  diets: [],
  excluded: [],
  disliked: [],
  max_cooking_minutes: null,
  notes: null,
  updated_by: null,
  updated_at: null,
};

test("saves preferences with comma-separated lists", async () => {
  const fetch = mockFetch({
    [`GET ${URL}`]: empty,
    [`PUT ${URL}`]: (_url: string, init: RequestInit) =>
      jsonResponse({
        ...JSON.parse(init.body as string),
        updated_by: "ala",
        updated_at: "2026-10-24T10:00:00Z",
      }),
  });
  renderWithProviders(<HouseholdPreferences />);

  await userEvent.type(await screen.findByLabelText("Liczba osób"), "4");
  await userEvent.type(screen.getByLabelText("Alergie i czego nie jemy"), "orzechy, seler,");
  await userEvent.type(screen.getByLabelText("Diety"), "wegetariańska");
  await userEvent.click(screen.getByRole("button", { name: "Zapisz preferencje" }));

  expect(await screen.findByText("Zapisano.")).toBeInTheDocument();
  const put = fetch.mock.calls.find(([, init]) => init?.method === "PUT")!;
  expect(JSON.parse(put[1]!.body as string)).toEqual({
    people: 4,
    diets: ["wegetariańska"],
    excluded: ["orzechy", "seler"],
    disliked: [],
    max_cooking_minutes: null,
    notes: null,
  });
  // Formularz pokazuje zapisaną wersję z serwera.
  expect(screen.getByLabelText("Alergie i czego nie jemy")).toHaveValue("orzechy, seler");
});

test("shows saved preferences and who changed them", async () => {
  mockFetch({
    [`GET ${URL}`]: {
      ...empty,
      people: 2,
      excluded: ["orzechy", "owoce morza"],
      notes: "tanio",
      updated_by: "ola",
      updated_at: "2026-10-24T10:00:00Z",
    },
  });
  renderWithProviders(<HouseholdPreferences />);

  expect(await screen.findByLabelText("Alergie i czego nie jemy")).toHaveValue(
    "orzechy, owoce morza",
  );
  expect(screen.getByLabelText("Liczba osób")).toHaveValue(2);
  expect(screen.getByLabelText("Inne uwagi")).toHaveValue("tanio");
  expect(screen.getByText("Ostatnio zmieniał(a): ola")).toBeInTheDocument();
});

test("refreshes the form after a change made elsewhere (e.g. chat)", async () => {
  mockFetch({ [`GET ${URL}`]: empty });
  const { queryClient } = renderWithProviders(<HouseholdPreferences />);
  const field = await screen.findByLabelText("Czego nie lubimy");
  expect(field).toHaveValue("");

  act(() => {
    queryClient.setQueryData(["household-preferences"], {
      ...empty,
      disliked: ["oliwki"],
      updated_by: "ala",
      updated_at: "2026-10-24T11:00:00Z",
    });
  });

  expect(await screen.findByDisplayValue("oliwki")).toBeInTheDocument();
});

test("shows server validation error", async () => {
  mockFetch({
    [`GET ${URL}`]: empty,
    [`PUT ${URL}`]: () => jsonResponse({ detail: [{ msg: "za mało" }] }, 422),
  });
  renderWithProviders(<HouseholdPreferences />);

  await userEvent.type(await screen.findByLabelText("Liczba osób"), "3");
  await userEvent.click(screen.getByRole("button", { name: "Zapisz preferencje" }));

  expect(
    await screen.findByText("Sprawdź poprawność wprowadzonych danych."),
  ).toBeInTheDocument();
  expect(screen.queryByText("Zapisano.")).not.toBeInTheDocument();
});
