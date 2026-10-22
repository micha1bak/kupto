import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type Modifier,
} from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ApiError, del, post, put } from "../api/client";
import { keys, useShoppingList } from "../api/queries";
import {
  CATEGORIES,
  UNITS,
  type Category,
  type CategoryGroup,
  type Item,
  type NeedCreate,
  type Shopper,
  type ShoppingList,
  type Unit,
} from "../api/types";
import { dropCategory, reorderGroups, type CategoryDrop } from "./categoryOrder";
import { formatQuantities, formatQuantity, formatTime } from "./format";
import styles from "./ListView.module.css";

function setItemBought(list: ShoppingList, itemId: number, bought: boolean): ShoppingList {
  return {
    ...list,
    groups: list.groups.map((g) => ({
      ...g,
      items: g.items.map((i) => (i.id === itemId ? { ...i, bought } : i)),
    })),
  };
}

function useListMutation<T>(fn: (arg: T) => Promise<ShoppingList>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (data) => queryClient.setQueryData(keys.list, data),
  });
}

function AddItemForm() {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [unit, setUnit] = useState<Unit | "">("");
  const [category, setCategory] = useState<Category | "">("");
  const add = useListMutation((need: NeedCreate) => post<ShoppingList>("/api/list/needs", need));

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    const parsed = amount ? Number(amount.replace(",", ".")) : null;
    add.mutate(
      {
        name: name.trim(),
        amount: parsed && parsed > 0 ? parsed : null,
        unit: unit || null,
        category: category || null,
      },
      {
        onSuccess: () => {
          setName("");
          setAmount("");
          setUnit("");
          setCategory("");
        },
      },
    );
  }

  return (
    <form className={styles.addForm} onSubmit={submit} aria-label="Dodaj ręcznie">
      <input
        aria-label="Produkt"
        placeholder="Dodaj produkt…"
        value={name}
        maxLength={100}
        onChange={(e) => setName(e.target.value)}
      />
      <input
        aria-label="Ilość"
        placeholder="Ilość"
        inputMode="decimal"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <select aria-label="Jednostka" value={unit} onChange={(e) => setUnit(e.target.value as Unit)}>
        <option value="">—</option>
        {UNITS.map((u) => (
          <option key={u}>{u}</option>
        ))}
      </select>
      <select
        className={styles.wide}
        aria-label="Kategoria"
        value={category}
        onChange={(e) => setCategory(e.target.value as Category)}
      >
        <option value="">Kategoria (automatycznie)</option>
        {CATEGORIES.map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
      <button className={`primary ${styles.wide}`} type="submit" disabled={add.isPending}>
        Dodaj
      </button>
      {add.error && (
        <p className={`error ${styles.wide}`}>
          {add.error instanceof ApiError ? add.error.message : "Nie udało się dodać."}
        </p>
      )}
    </form>
  );
}

function ItemRow({ item, userId }: { item: Item; userId: number }) {
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (bought: boolean) =>
      (bought ? post : del)<ShoppingList>(`/api/list/items/${item.id}/bought`),
    // Optymistycznie: odhaczenie widać od razu, a przy błędzie stan wraca.
    onMutate: async (bought) => {
      await queryClient.cancelQueries({ queryKey: keys.list });
      const previous = queryClient.getQueryData<ShoppingList>(keys.list);
      if (previous) queryClient.setQueryData(keys.list, setItemBought(previous, item.id, bought));
      return { previous };
    },
    onError: (_e, _v, context) => queryClient.setQueryData(keys.list, context?.previous),
    onSuccess: (data) => queryClient.setQueryData(keys.list, data),
  });
  const remove = useListMutation(() => del<ShoppingList>(`/api/list/items/${item.id}`));
  const withdraw = useListMutation((needId: number) => del<ShoppingList>(`/api/list/needs/${needId}`));

  return (
    <li className={`${styles.item} ${item.bought ? styles.bought : ""}`}>
      <input
        type="checkbox"
        checked={item.bought}
        aria-label={`Kupione: ${item.name}`}
        onChange={(e) => toggle.mutate(e.target.checked)}
      />
      <div>
        <span className={styles.name}>
          {item.name}
          {item.quantities.length > 0 && (
            <span className={styles.quantity}>{formatQuantities(item.quantities)}</span>
          )}
        </span>
        <ul className={styles.needs}>
          {item.needs.map((need) => (
            <li key={need.id}>
              {need.login ?? "ktoś"}
              {need.amount !== null && `: ${formatQuantity(need.amount, need.unit)}`}
              {need.note && ` (${need.note})`}
              {need.user_id === userId && (
                <button
                  onClick={() => withdraw.mutate(need.id)}
                  aria-label={`Wycofaj moje zapotrzebowanie: ${item.name}`}
                  title="Wycofaj moje zapotrzebowanie"
                >
                  ×
                </button>
              )}
            </li>
          ))}
          {item.bought && item.bought_by && <li>kupione przez {item.bought_by}</li>}
        </ul>
      </div>
      <button
        className={styles.iconButton}
        onClick={() => remove.mutate(undefined)}
        aria-label={`Usuń ${item.name}`}
        title="Usuń pozycję"
      >
        🗑
      </button>
    </li>
  );
}

const categoryPath = (category: Category) => `/api/list/category-order/${encodeURIComponent(category)}`;

/** Przytrzymanie na dotyku (ms), zanim nagłówek da się przeciągnąć — w sklepie nic nie przesunie się przypadkiem. */
export const TOUCH_HOLD_MS = 400;

// Kategorie przesuwa się tylko w pionie.
const verticalOnly: Modifier = ({ transform }) => ({ ...transform, x: 0 });

const screenReaderInstructions = {
  draggable:
    "Aby przenieść kategorię, naciśnij spację lub Enter, wybierz miejsce strzałkami w górę i w dół, " +
    "a potem naciśnij spację lub Enter, by ją tam przypiąć. Escape anuluje. Na ekranie dotykowym przytrzymaj nagłówek.",
};

const announcements: Announcements = {
  onDragStart: ({ active }) => `Podniesiono kategorię ${active.id}.`,
  onDragOver: ({ active, over }) =>
    over ? `Kategoria ${active.id} jest w miejscu kategorii ${over.id}.` : `Kategoria ${active.id} jest poza listą.`,
  onDragEnd: ({ active, over }) =>
    over && over.id !== active.id
      ? `Kategoria ${active.id} przypięta w miejscu kategorii ${over.id}.`
      : `Kategoria ${active.id} została na swoim miejscu.`,
  onDragCancel: ({ active }) => `Anulowano przenoszenie kategorii ${active.id}.`,
};

function GroupSection({ group, userId }: { group: CategoryGroup; userId: number }) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: group.category,
    attributes: { roleDescription: "przesuwalna kategoria" },
  });
  const unpin = useListMutation(() => del<ShoppingList>(categoryPath(group.category)));

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={`${styles.group} ${isDragging ? styles.dragging : ""}`}
    >
      <h3 className={styles.groupHeader}>
        <span ref={setActivatorNodeRef} className={styles.handle} {...attributes} {...listeners}>
          {group.category}
          {group.pinned && (
            <span className={styles.pin} role="img" aria-label="przypięta" title="Przypięta">
              📌
            </span>
          )}
        </span>
        {group.pinned && (
          <button
            className={styles.unpin}
            onClick={() => unpin.mutate(undefined)}
            disabled={unpin.isPending}
            aria-label={`Odepnij kategorię ${group.category}`}
          >
            Odepnij
          </button>
        )}
      </h3>
      <ul className={styles.items} aria-label={group.category}>
        {group.items.map((item) => (
          <ItemRow key={item.id} item={item} userId={userId} />
        ))}
      </ul>
    </div>
  );
}

/** Kto z gospodarstwa robi teraz zakupy — „Robisz zakupy od 14:05”, „ania robi zakupy od 13:50”. */
function ShoppersBanner({ shoppers, userId }: { shoppers: Shopper[]; userId: number }) {
  if (shoppers.length === 0) return null;
  return (
    <ul className={styles.shoppers} aria-label="Kto robi zakupy">
      {shoppers.map((s) => (
        <li key={s.user_id}>
          🛒 {s.user_id === userId ? "Robisz zakupy" : `${s.login} robi zakupy`} od {formatTime(s.since)}
        </li>
      ))}
    </ul>
  );
}

function useCategoryPin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ category, after, before }: CategoryDrop) =>
      put<ShoppingList>(categoryPath(category), { after, before }),
    // Optymistycznie, jak przy odhaczaniu: grupa zostaje tam, gdzie ją upuszczono.
    onMutate: async (drop) => {
      await queryClient.cancelQueries({ queryKey: keys.list });
      const previous = queryClient.getQueryData<ShoppingList>(keys.list);
      if (previous) queryClient.setQueryData(keys.list, reorderGroups(previous, drop.order, drop.category));
      return { previous };
    },
    onError: (_e, _v, context) => queryClient.setQueryData(keys.list, context?.previous),
    onSuccess: (data) => queryClient.setQueryData(keys.list, data),
  });
}

export function ListView({ userId }: { userId: number }) {
  const list = useShoppingList();
  const finish = useListMutation(() => post<ShoppingList>("/api/list/finish"));
  const startShopping = useListMutation(() => post<ShoppingList>("/api/list/shopping"));
  const stopShopping = useListMutation(() => del<ShoppingList>("/api/list/shopping"));
  const resetOrder = useListMutation(() => del<ShoppingList>("/api/list/category-order"));
  const pin = useCategoryPin();
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: TOUCH_HOLD_MS, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const groups = list.data?.groups ?? [];
  const order = groups.map((g) => g.category);
  const anyBought = groups.some((g) => g.items.some((i) => i.bought));
  const anyPinned = groups.some((g) => g.pinned);
  const shoppers = list.data?.shoppers ?? [];
  const imShopping = shoppers.some((s) => s.user_id === userId);
  const shoppingError = startShopping.error ?? stopShopping.error;

  function confirmFinish() {
    if (window.confirm("Zakończyć zakupy? Kupione pozycje zostaną przeniesione do historii.")) {
      finish.mutate(undefined);
    }
  }

  function confirmResetOrder() {
    if (window.confirm("Przywrócić automatyczną kolejność kategorii? Wszystkie przypięcia zostaną usunięte.")) {
      resetOrder.mutate(undefined);
    }
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    const drop = dropCategory(order, active.id as Category, (over?.id as Category | undefined) ?? null);
    if (drop) pin.mutate(drop);
  }

  return (
    <section className={styles.view} aria-label="Lista zakupów">
      <div className={styles.toolbar}>
        <h2>Lista</h2>
        <div className={styles.actions}>
          {imShopping ? (
            <button
              onClick={() => stopShopping.mutate(undefined)}
              disabled={stopShopping.isPending}
              title="Przestań pokazywać domownikom, że robisz zakupy (kupione zostają na liście)"
            >
              Kończę
            </button>
          ) : (
            <button
              className="primary"
              onClick={() => startShopping.mutate(undefined)}
              disabled={startShopping.isPending || !list.data}
              title="Pokaż domownikom, że robisz zakupy (status wygasa sam po 3 godzinach)"
            >
              Idę na zakupy
            </button>
          )}
          {anyPinned && (
            <button
              onClick={confirmResetOrder}
              disabled={resetOrder.isPending}
              title="Przywróć automatyczną kolejność kategorii"
            >
              Przywróć kolejność
            </button>
          )}
          {anyBought && (
            <button onClick={confirmFinish} disabled={finish.isPending}>
              Zakończ zakupy
            </button>
          )}
        </div>
      </div>
      <ShoppersBanner shoppers={shoppers} userId={userId} />
      {shoppingError && (
        <p className="error">
          {shoppingError instanceof ApiError ? shoppingError.message : "Nie udało się zmienić statusu zakupów."}
        </p>
      )}
      {list.isLoading && <p className="muted">Ładowanie…</p>}
      {list.data && groups.length === 0 && (
        <p className={`muted ${styles.empty}`}>
          Lista jest pusta. Napisz w czacie, czego potrzebujesz, albo dodaj produkt poniżej.
        </p>
      )}
      {pin.error && (
        <p className="error">
          {pin.error instanceof ApiError ? pin.error.message : "Nie udało się zapisać kolejności."}
        </p>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[verticalOnly]}
        onDragEnd={handleDragEnd}
        accessibility={{ announcements, screenReaderInstructions }}
      >
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          {groups.map((group) => (
            <GroupSection key={group.category} group={group} userId={userId} />
          ))}
        </SortableContext>
      </DndContext>
      <AddItemForm />
    </section>
  );
}
