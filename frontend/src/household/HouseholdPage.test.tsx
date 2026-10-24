import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HouseholdPage, HouseholdSetup } from "./HouseholdPage";
import { jsonResponse, mockFetch, renderWithProviders, testProfile } from "../test/utils";

afterEach(() => vi.unstubAllGlobals());

const household = {
  id: 1,
  name: "Dom",
  members: [
    { id: 1, name: "Ala", is_owner: true, joined_at: null },
    { id: 2, name: "Ola", is_owner: false, joined_at: null },
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

function profile(id: number, name: string) {
  return testProfile({ id, name, email: `${name.toLowerCase()}@example.com` });
}

test("owner sees management controls", async () => {
  const fetch = mockFetch({
    "GET /api/users/me": profile(1, "Ala"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
    "POST /api/households/me/members": () =>
      jsonResponse(
        { ...household, members: [...household.members, { id: 3, name: "Ewa", is_owner: false }] },
        201,
      ),
  });
  renderWithProviders(<HouseholdPage />);

  const members = await screen.findByRole("list", { name: "Członkowie" });
  expect(within(members).getByText("właściciel")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Usuń Ola" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Usuń Ala" })).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Adres e-mail domownika"), " ewa@example.com ");
  await userEvent.click(screen.getByRole("button", { name: "Dodaj" }));

  expect(await within(members).findByText("Ewa")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.calls.at(-1)![1]!.body as string)).toEqual({
    email: "ewa@example.com",
  });
});

test("regular member cannot manage members", async () => {
  mockFetch({
    "GET /api/users/me": profile(2, "Ola"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
  });
  renderWithProviders(<HouseholdPage />);

  await screen.findByRole("list", { name: "Członkowie" });
  expect(screen.queryByRole("button", { name: /Usuń/ })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Adres e-mail domownika")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Opuść gospodarstwo" })).toBeInTheDocument();
});

test("add member shows server error", async () => {
  mockFetch({
    "GET /api/users/me": profile(1, "Ala"),
    "GET /api/households/me": household,
    "GET /api/households/me/preferences": emptyPreferences,
    "POST /api/households/me/members": () =>
      jsonResponse({ detail: "Nie znaleziono konta o tym adresie e-mail." }, 404),
  });
  renderWithProviders(<HouseholdPage />);

  await userEvent.type(await screen.findByLabelText("Adres e-mail domownika"), "nikt@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Dodaj" }));

  expect(await screen.findByText("Nie znaleziono konta o tym adresie e-mail.")).toBeInTheDocument();
});

test("setup shows own address and creates household", async () => {
  const fetch = mockFetch({
    "POST /api/households": () => jsonResponse(household, 201),
  });
  renderWithProviders(<HouseholdSetup profile={testProfile({ household: null })} />);

  expect(screen.getByText("ala@example.com")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Utwórz" }));

  await vi.waitFor(() =>
    expect(fetch).toHaveBeenCalledWith("/api/households", expect.objectContaining({ method: "POST" })),
  );
});

test("setup asks to confirm the address before joining", () => {
  renderWithProviders(
    <HouseholdSetup
      profile={testProfile({ household: null, email_verified: false, email_status: "unverified" })}
    />,
  );

  expect(screen.getByText(/najpierw potwierdź go/)).toBeInTheDocument();
});

test("setup of a legacy account without address shows its login", () => {
  renderWithProviders(
    <HouseholdSetup
      profile={testProfile({
        household: null,
        login: "stary",
        email: null,
        email_verified: false,
        email_status: "missing",
        mail_enabled: false,
      })}
    />,
  );

  expect(screen.getByText("stary")).toBeInTheDocument();
});
