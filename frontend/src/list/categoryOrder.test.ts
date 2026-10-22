import type { Category, ShoppingList } from "../api/types";
import { dropCategory, reorderGroups } from "./categoryOrder";

const order: Category[] = ["Pieczywo", "Nabiał", "Chemia i higiena"];

test("dropping on the first group moves the category to the start", () => {
  expect(dropCategory(order, "Chemia i higiena", "Pieczywo")).toEqual({
    category: "Chemia i higiena",
    order: ["Chemia i higiena", "Pieczywo", "Nabiał"],
    after: null,
    before: "Pieczywo",
  });
});

test("dropping on the last group moves the category to the end", () => {
  expect(dropCategory(order, "Pieczywo", "Chemia i higiena")).toEqual({
    category: "Pieczywo",
    order: ["Nabiał", "Chemia i higiena", "Pieczywo"],
    after: "Chemia i higiena",
    before: null,
  });
});

test("dropping in the middle names both neighbours", () => {
  expect(dropCategory(order, "Chemia i higiena", "Nabiał")).toMatchObject({
    order: ["Pieczywo", "Chemia i higiena", "Nabiał"],
    after: "Pieczywo",
    before: "Nabiał",
  });
});

test("dropping in place or outside the list changes nothing", () => {
  expect(dropCategory(order, "Nabiał", "Nabiał")).toBeNull();
  expect(dropCategory(order, "Nabiał", null)).toBeNull();
});

test("reorderGroups applies the new order and marks the moved category as pinned", () => {
  const list: ShoppingList = {
    id: 1,
    groups: order.map((category) => ({ category, pinned: category === "Nabiał", items: [] })),
    shoppers: [],
  };

  const next = reorderGroups(list, ["Chemia i higiena", "Pieczywo", "Nabiał"], "Chemia i higiena");

  expect(next.groups.map((g) => [g.category, g.pinned])).toEqual([
    ["Chemia i higiena", true],
    ["Pieczywo", false],
    ["Nabiał", true],
  ]);
});
