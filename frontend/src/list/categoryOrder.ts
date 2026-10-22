import { arrayMove } from "@dnd-kit/sortable";
import type { Category, CategoryMove, ShoppingList } from "../api/types";

export interface Drop<T> {
  /** Kolejność widocznych elementów po upuszczeniu. */
  order: T[];
  /** Sąsiedzi upuszczonego elementu; `null` = początek albo koniec. */
  after: T | null;
  before: T | null;
}

/** Wynik upuszczenia elementu `active` w miejscu `over`; `null`, gdy kolejność się nie zmienia. */
export function dropInOrder<T>(order: T[], active: T, over: T | null): Drop<T> | null {
  const from = order.indexOf(active);
  const to = over === null ? -1 : order.indexOf(over);
  if (from < 0 || to < 0 || from === to) return null;
  const next = arrayMove(order, from, to);
  return { order: next, after: next[to - 1] ?? null, before: next[to + 1] ?? null };
}

export interface CategoryDrop extends CategoryMove {
  category: Category;
  /** Kolejność widocznych grup po upuszczeniu. */
  order: Category[];
}

/** Wynik upuszczenia nagłówka `active` w miejscu `over`; `null`, gdy kolejność się nie zmienia. */
export function dropCategory(order: Category[], active: Category, over: Category | null): CategoryDrop | null {
  const drop = dropInOrder(order, active, over);
  return drop && { category: active, ...drop };
}

/** Lista z grupami w kolejności `order` i przypiętą kategorią `pinned` (aktualizacja optymistyczna). */
export function reorderGroups(list: ShoppingList, order: Category[], pinned: Category): ShoppingList {
  const byCategory = new Map(list.groups.map((g) => [g.category, g]));
  return {
    ...list,
    groups: order.flatMap((category) => {
      const group = byCategory.get(category);
      return group ? [{ ...group, pinned: group.pinned || category === pinned }] : [];
    }),
  };
}
