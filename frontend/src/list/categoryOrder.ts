import { arrayMove } from "@dnd-kit/sortable";
import type { Category, CategoryMove, ShoppingList } from "../api/types";

export interface CategoryDrop extends CategoryMove {
  category: Category;
  /** Kolejność widocznych grup po upuszczeniu. */
  order: Category[];
}

/** Wynik upuszczenia nagłówka `active` w miejscu `over`; `null`, gdy kolejność się nie zmienia. */
export function dropCategory(order: Category[], active: Category, over: Category | null): CategoryDrop | null {
  const from = order.indexOf(active);
  const to = over === null ? -1 : order.indexOf(over);
  if (from < 0 || to < 0 || from === to) return null;
  const next = arrayMove(order, from, to);
  return { category: active, order: next, after: next[to - 1] ?? null, before: next[to + 1] ?? null };
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
