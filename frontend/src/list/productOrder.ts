import type { Category, ItemMove, ShoppingList } from "../api/types";
import { dropInOrder } from "./categoryOrder";

export interface ItemDrop extends ItemMove {
  itemId: number;
  category: Category;
  /** Kolejność id pozycji grupy po upuszczeniu. */
  order: number[];
}

/** Wynik upuszczenia pozycji `active` w miejscu `over` w grupie `category`; `null`, gdy nic się nie zmienia. */
export function dropItem(category: Category, order: number[], active: number, over: number | null): ItemDrop | null {
  const drop = dropInOrder(order, active, over);
  return drop && { itemId: active, category, ...drop };
}

/** Lista z pozycjami grupy w kolejności `drop.order` i przypiętą przeniesioną pozycją (aktualizacja optymistyczna). */
export function reorderItems(list: ShoppingList, drop: ItemDrop): ShoppingList {
  return {
    ...list,
    groups: list.groups.map((group) => {
      if (group.category !== drop.category) return group;
      const rank = new Map(drop.order.map((id, index) => [id, index]));
      // Pozycja spoza `drop.order` (np. dodana w międzyczasie) zostaje na końcu, do odpowiedzi serwera.
      const items = [...group.items].sort(
        (a, b) => (rank.get(a.id) ?? rank.size) - (rank.get(b.id) ?? rank.size),
      );
      return { ...group, items: items.map((i) => (i.id === drop.itemId ? { ...i, pinned: true } : i)) };
    }),
  };
}
