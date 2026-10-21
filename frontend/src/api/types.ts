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

export interface ShoppingList {
  id: number;
  groups: { category: Category; items: Item[] }[];
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
