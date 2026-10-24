import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { keys } from "../api/queries";
import type { Recipe, RecipeIngredient, RecipeToList } from "../api/types";
import { formatQuantity } from "../list/format";
import styles from "./RecipesPage.module.css";

/** „mleko — 0,5 l”, „mąka — 2 szklanki”, „jajka — 2 szt (duże)”. */
export function ingredientLabel(ingredient: Omit<RecipeIngredient, "id">): string {
  const details = [formatQuantity(ingredient.amount, ingredient.unit), ingredient.note]
    .filter(Boolean)
    .join(" ");
  return details ? `${ingredient.name} — ${details}` : ingredient.name;
}

/** Komunikat po dodaniu składników: co dodano i co już było na liście. */
export function addedMessage(result: RecipeToList): string {
  const names = result.added.map((a) =>
    a.already_on_list ? `${a.name} (już było na liście)` : a.name,
  );
  return `Dodano na listę: ${names.join(", ")}.`;
}

/**
 * Składniki przepisu do zaznaczenia, czego brakuje w domu, i dodania na listę (notatka
 * „na: <danie>” po stronie serwera). Wspólne dla strony przepisu i kalendarza posiłków.
 */
export function IngredientsToList({ recipe }: { recipe: Recipe }) {
  const queryClient = useQueryClient();
  // Domyślnie nic nie jest zaznaczone — użytkownik wskazuje, czego brakuje w domu.
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [result, setResult] = useState<string | null>(null);

  const toList = useMutation({
    mutationFn: (ids: number[]) =>
      post<RecipeToList>(`/api/recipes/${recipe.id}/to-list`, { ingredient_ids: ids }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: keys.list });
      setSelected(new Set());
      setResult(addedMessage(data));
    },
  });

  function toggle(ingredientId: number) {
    setResult(null);
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(ingredientId)) next.delete(ingredientId);
      else next.add(ingredientId);
      return next;
    });
  }

  return (
    <>
      <p className={styles.meta}>Zaznacz, czego brakuje w domu.</p>
      <ul className={styles.rows} aria-label="Składniki">
        {recipe.ingredients.map((ingredient) => (
          <li key={ingredient.id} className={styles.row}>
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={selected.has(ingredient.id)}
                onChange={() => toggle(ingredient.id)}
              />
              {ingredientLabel(ingredient)}
            </label>
          </li>
        ))}
      </ul>
      <button
        className={`primary ${styles.submit}`}
        disabled={selected.size === 0 || toList.isPending}
        onClick={() =>
          // Kolejność z przepisu, niezależnie od kolejności zaznaczania.
          toList.mutate(recipe.ingredients.filter((i) => selected.has(i.id)).map((i) => i.id))
        }
      >
        Dodaj zaznaczone na listę
      </button>
      {result && (
        <p className={styles.result} role="status">
          {result}
        </p>
      )}
      {toList.error && (
        <p className="error">
          {toList.error instanceof ApiError ? toList.error.message : "Brak połączenia z serwerem."}
        </p>
      )}
    </>
  );
}
