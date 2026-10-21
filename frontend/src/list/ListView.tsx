import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, del, post } from "../api/client";
import { keys, useShoppingList } from "../api/queries";
import {
  CATEGORIES,
  UNITS,
  type Category,
  type Item,
  type NeedCreate,
  type ShoppingList,
  type Unit,
} from "../api/types";
import { formatQuantities, formatQuantity } from "./format";
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

export function ListView({ userId }: { userId: number }) {
  const list = useShoppingList();
  const finish = useListMutation(() => post<ShoppingList>("/api/list/finish"));
  const groups = list.data?.groups ?? [];
  const anyBought = groups.some((g) => g.items.some((i) => i.bought));

  function confirmFinish() {
    if (window.confirm("Zakończyć zakupy? Kupione pozycje zostaną usunięte z listy.")) {
      finish.mutate(undefined);
    }
  }

  return (
    <section className={styles.view} aria-label="Lista zakupów">
      <div className={styles.toolbar}>
        <h2>Lista</h2>
        {anyBought && (
          <button onClick={confirmFinish} disabled={finish.isPending}>
            Zakończ zakupy
          </button>
        )}
      </div>
      {list.isLoading && <p className="muted">Ładowanie…</p>}
      {list.data && groups.length === 0 && (
        <p className={`muted ${styles.empty}`}>
          Lista jest pusta. Napisz w czacie, czego potrzebujesz, albo dodaj produkt poniżej.
        </p>
      )}
      {groups.map((group) => (
        <div key={group.category} className={styles.group}>
          <h3>{group.category}</h3>
          <ul className={styles.items} aria-label={group.category}>
            {group.items.map((item) => (
              <ItemRow key={item.id} item={item} userId={userId} />
            ))}
          </ul>
        </div>
      ))}
      <AddItemForm />
    </section>
  );
}
