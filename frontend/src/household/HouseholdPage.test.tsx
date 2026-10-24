import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HouseholdPage, HouseholdSetup } from "./HouseholdPage";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

const household = {
  id: 1,
  name: "Dom",
  members: [
    { id: 1, login: "ala", is_owner: true, joined_at: null },
    { id: 2, login: "ola", is_owner: false, joined_at: null },
  ],
};

const emptyPreferences = {
  people: null,
  diets: [],
  excluded: [],
  disliked: [],
  max_cooking_minutes: null,
  notes: null,
  updated_by: null,
  updated_at: null,
};

function profile(id: number, login: string) {
  return { id, login, household: { id: 1, name: "Dom" } };
}

test("owner sees management controls", async () => {
  const fetch = mockFetch({
    "GET /api/users/me": profile(1, "ala"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
    "POST /api/households/me/members": () =>
      jsonResponse(
        { ...household, members: [...household.members, { id: 3, login: "ewa", is_owner: false }] },
        201,
      ),
  });
  renderWithProviders(<HouseholdPage />);

  const members = await screen.findByRole("list", { name: "Członkowie" });
  expect(within(members).getByText("właściciel")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Usuń ola" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Usuń ala" })).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Login domownika"), "ewa");
  await userEvent.click(screen.getByRole("button", { name: "Dodaj" }));

  expect(await within(members).findByText("ewa")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.calls.at(-1)![1]!.body as string)).toEqual({ login: "ewa" });
});

test("regular member cannot manage members", async () => {
  mockFetch({
    "GET /api/users/me": profile(2, "ola"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
  });
  renderWithProviders(<HouseholdPage />);

  await screen.findByRole("list", { name: "Członkowie" });
  expect(screen.queryByRole("button", { name: /Usuń/ })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Login domownika")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Opuść gospodarstwo" })).toBeInTheDocument();
});

test("add member shows server error", async () => {
  mockFetch({
    "GET /api/users/me": profile(1, "ala"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
    "POST /api/households/me/members": () =>
      jsonResponse({ detail: "Użytkownik o tym loginie nie istnieje." }, 404),
  });
  renderWithProviders(<HouseholdPage />);

  await userEvent.type(await screen.findByLabelText("Login domownika"), "nikt");
  await userEvent.click(screen.getByRole("button", { name: "Dodaj" }));

  expect(await screen.findByText("Użytkownik o tym loginie nie istnieje.")).toBeInTheDocument();
});

test("setup shows own login and creates household", async () => {
  const fetch = mockFetch({
    "POST /api/households": () => jsonResponse(household, 201),
  });
  renderWithProviders(<HouseholdSetup login="ala" />);

  expect(screen.getByText("ala")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Utwórz" }));

  await vi.waitFor(() =>
    expect(fetch).toHaveBeenCalledWith("/api/households", expect.objectContaining({ method: "POST" })),
  );
});
