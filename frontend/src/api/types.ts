export type Category =
  | "Warzywa i owoce"
  | "Pieczywo"
  | "Nabiał"
  | "Mięso i ryby"
  | "Mrożonki"
  | "Produkty suche"
  | "Napoje"
  | "Słodycze i przekąski"
  | "Chemia i higiena"
  | "Inne";

export const CATEGORIES: Category[] = [
  "Warzywa i owoce",
  "Pieczywo",
  "Nabiał",
  "Mięso i ryby",
  "Mrożonki",
  "Produkty suche",
  "Napoje",
  "Słodycze i przekąski",
  "Chemia i higiena",
  "Inne",
];

export type Unit = "szt" | "kg" | "g" | "l" | "ml" | "opak";
export const UNITS: Unit[] = ["szt", "kg", "g", "l", "ml", "opak"];

export interface Profile {
  id: number;
  login: string;
  household: { id: number; name: string } | null;
}

export interface Member {
  id: number;
  login: string;
  is_owner: boolean;
  joined_at: string | null;
}

export interface Household {
  id: number;
  name: string;
  members: Member[];
}

export interface Quantity {
  amount: number;
  unit: Unit | null;
}

export interface Need {
  id: number;
  user_id: number | null;
  login: string | null;
  amount: number | null;
  unit: Unit | null;
  note: string | null;
  created_at: string;
}

export interface Item {
  id: number;
  name: string;
  category: Category;
  quantities: Quantity[];
  needs: Need[];
  bought: boolean;
  bought_at: string | null;
  bought_by: string | null;
}

export interface CategoryGroup {
  category: Category;
  /** Czy zalogowany użytkownik przypiął tę kategorię na jej miejscu. */
  pinned: boolean;
  items: Item[];
}

/** Członek gospodarstwa ze statusem „robię zakupy” (status wygasa sam o `expires_at`). */
export interface Shopper {
  user_id: number;
  login: string;
  since: string;
  expires_at: string;
}

export interface ShoppingList {
  id: number;
  /** Grupy w kolejności kategorii zalogowanego użytkownika. */
  groups: CategoryGroup[];
  /** Kto z gospodarstwa robi teraz zakupy; najdawniej rozpoczęty pierwszy. */
  shoppers: Shopper[];
}

/** Sąsiedzi przeniesionej kategorii; brak sąsiada oznacza początek albo koniec kolejności. */
export interface CategoryMove {
  after: Category | null;
  before: Category | null;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface NeedCreate {
  name: string;
  amount?: number | null;
  unit?: Unit | null;
  note?: string | null;
  category?: Category | null;
}

/** Zapotrzebowanie, które doprowadziło do zakupu pozycji z historii. */
export interface PurchasedNeed {
  user_id: number | null;
  login: string | null;
  amount: number | null;
  unit: Unit | null;
  note: string | null;
  requested_at: string;
}

export interface PurchasedItem {
  id: number;
  name: string;
  category: Category;
  quantities: Quantity[];
  needs: PurchasedNeed[];
  bought_at: string;
  bought_by: string | null;
}

/** Jedno zakończenie zakupów; grupy w kolejności kategorii zalogowanego użytkownika. */
export interface ShoppingTrip {
  id: number;
  finished_at: string;
  finished_by: string | null;
  item_count: number;
  groups: { category: Category; items: PurchasedItem[] }[];
}

export interface TripPage {
  trips: ShoppingTrip[];
  /** Wartość `before` dla starszej strony; null — to już cała historia. */
  next_cursor: number | null;
}

/** Produkt znaleziony w historii: kiedy i kto kupił go ostatnio. */
export interface ProductHit {
  name: string;
  category: Category;
  last_bought_at: string;
  last_bought_by: string | null;
  last_trip_id: number;
  last_quantities: Quantity[];
  times_bought: number;
}

/** Produkt kupowany zwykle, którego nie ma teraz na liście (`GET /api/history/usual`). */
export interface UsualProduct {
  name: string;
  category: Category;
  amount: number | null;
  unit: Unit | null;
  times_bought: number;
  typical_interval_days: number;
  last_bought_at: string;
  overdue: number;
}
