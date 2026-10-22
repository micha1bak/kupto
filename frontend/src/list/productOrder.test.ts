import type { ShoppingList } from "../api/types";
import { dropItem, reorderItems } from "./productOrder";

const order = [20, 21, 22];

test("dropping an item names its neighbours by id", () => {
  expect(dropItem("Nabiał", order, 22, 20)).toEqual({
    itemId: 22,
    category: "Nabiał",
    order: [22, 20, 21],
    after: null,
    before: 20,
  });
  expect(dropItem("Nabiał", order, 20, 22)).toMatchObject({ order: [21, 22, 20], after: 22, before: null });
  expect(dropItem("Nabiał", order, 22, 21)).toMatchObject({ order: [20, 22, 21], after: 20, before: 21 });
});

test("dropping an item in place or outside its group changes nothing", () => {
  expect(dropItem("Nabiał", order, 21, 21)).toBeNull();
  expect(dropItem("Nabiał", order, 21, null)).toBeNull();
  expect(dropItem("Nabiał", order, 21, 99)).toBeNull();
});

test("reorderItems reorders one group, pins the moved item and keeps unknown items last", () => {
  const item = (id: number, pinned = false) => ({
    id,
    name: `p${id}`,
    category: "Nabiał" as const,
    quantities: [],
    needs: [],
    bought: false,
    bought_at: null,
    bought_by: null,
    pinned,
  });
  const list: ShoppingList = {
    id: 1,
    groups: [
      { category: "Nabiał", pinned: false, items: [item(20), item(21, true), item(23), item(22)] },
      { category: "Pieczywo", pinned: false, items: [{ ...item(30), category: "Pieczywo" }] },
    ],
    shoppers: [],
  };

  const next = reorderItems(list, { itemId: 22, category: "Nabiał", order: [22, 20, 21], after: null, before: 20 });

  expect(next.groups[0].items.map((i) => [i.id, i.pinned])).toEqual([
    [22, true],
    [20, false],
    [21, true],
    [23, false],
  ]);
  expect(next.groups[1]).toBe(list.groups[1]);
});
