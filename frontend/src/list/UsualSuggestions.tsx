import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { keys, useUsualProducts } from "../api/queries";
import type { NeedCreate, ShoppingList, UsualProduct } from "../api/types";
import { formatQuantity } from "./format";
import styles from "./UsualSuggestions.module.css";

/** Ile podpowiedzi pokazujemy naraz — reszta pojawi się, gdy te trafią na listę. */
export const MAX_SHOWN = 6;

/** Klucz w localStorage: lokalna data (RRRR-MM-DD), na którą ukryto podpowiedzi. */
export const HIDDEN_ON_KEY = "kupto.usualHiddenOn";

export function today(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function hiddenToday(): boolean {
  try {
    return localStorage.getItem(HIDDEN_ON_KEY) === today();
  } catch {
    return false; // bez dostępu do pamięci przeglądarki podpowiedź po prostu się pokazuje
  }
}

function hideForToday() {
  try {
    localStorage.setItem(HIDDEN_ON_KEY, today());
  } catch {
    // ukrycie zadziała do przeładowania strony
  }
}

/** Jak `normalize_name` w backendzie: pojedyncze spacje, małe litery. */
const normalize = (name: string) => name.trim().split(/\s+/).join(" ").toLowerCase();

/**
 * Dyskretna podpowiedź nad listą: „Zwykle kupujecie: mleko, chleb…” z dodaniem jednym kliknięciem
 * (zwykłe zapotrzebowanie z typową ilością) i ukryciem do końca dnia.
 */
export function UsualSuggestions({ list }: { list: ShoppingList | undefined }) {
  const usual = useUsualProducts();
  const queryClient = useQueryClient();
  const [hidden, setHidden] = useState(hiddenToday);
  const add = useMutation({
    mutationFn: (product: UsualProduct) =>
      post<ShoppingList>("/api/list/needs", {
        name: product.name,
        amount: product.amount,
        unit: product.unit,
        category: product.category,
      } satisfies NeedCreate),
    onSuccess: (data) => queryClient.setQueryData(keys.list, data),
  });

  if (hidden || !list || !usual.data) return null;
  // Podpowiedzi liczone przy pobraniu; dodany w międzyczasie produkt chowamy od razu.
  const onList = new Set(list.groups.flatMap((g) => g.items.map((i) => normalize(i.name))));
  const missing = usual.data.filter((p) => !onList.has(normalize(p.name))).slice(0, MAX_SHOWN);
  if (missing.length === 0) return null;

  return (
    <aside className={styles.usual} aria-label="Zwykle kupujecie">
      <span className={styles.label}>Zwykle kupujecie:</span>
      <ul className={styles.products}>
        {missing.map((p) => (
          <li key={p.name}>
            <button
              onClick={() => add.mutate(p)}
              disabled={add.isPending}
              aria-label={`Dodaj ${p.name}${p.amount !== null ? ` (${formatQuantity(p.amount, p.unit)})` : ""}`}
              title={`Kupowane mniej więcej co ${Math.round(p.typical_interval_days)} dni`}
            >
              + {p.name}
              {p.amount !== null && <span className={styles.amount}> {formatQuantity(p.amount, p.unit)}</span>}
            </button>
          </li>
        ))}
      </ul>
      <button
        className={styles.hide}
        onClick={() => {
          hideForToday();
          setHidden(true);
        }}
      >
        Ukryj na dziś
      </button>
      {add.error && (
        <p className="error">{add.error instanceof ApiError ? add.error.message : "Nie udało się dodać."}</p>
      )}
    </aside>
  );
}
