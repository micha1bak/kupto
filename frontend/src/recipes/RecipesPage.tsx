import { useState, type FormEvent } from "react";
import { Link, useMatch, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, del, post, put } from "../api/client";
import { keys, useRecipe, useRecipes } from "../api/queries";
import {
  UNITS,
  type Category,
  type Recipe,
  type RecipeIngredient,
  type RecipeInput,
  type RecipeToList,
  type Unit,
} from "../api/types";
import { formatQuantity } from "../list/format";
import styles from "./RecipesPage.module.css";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Brak połączenia z serwerem.";
}

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

function RecipeList() {
  const recipes = useRecipes();

  return (
    <>
      <div className={styles.heading}>
        <h2 className={styles.title}>Nasze przepisy</h2>
        <Link className={styles.action} to="/recipes/new">
          Nowy przepis
        </Link>
      </div>
      {recipes.isPending ? (
        <p className="muted">Ładowanie…</p>
      ) : recipes.isError ? (
        <p className="error">{errorMessage(recipes.error)}</p>
      ) : recipes.data.length === 0 ? (
        <p className="muted">
          Nie macie jeszcze zapisanych przepisów. Dodaj przepis tutaj albo napisz w czacie
          „zapisz ten przepis” po wklejeniu przepisu lub linku.
        </p>
      ) : (
        <ul className={`card ${styles.rows}`} aria-label="Przepisy">
          {recipes.data.map((recipe) => (
            <li key={recipe.id} className={styles.row}>
              <Link to={`/recipes/${recipe.id}`} className={styles.name}>
                {recipe.name}
              </Link>
              <span className={styles.meta}>
                {[recipe.servings, `składniki: ${recipe.ingredient_count}`]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function RecipeDetail({ id }: { id: number }) {
  const recipe = useRecipe(id);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  // Domyślnie nic nie jest zaznaczone — użytkownik wskazuje, czego brakuje w domu.
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [result, setResult] = useState<string | null>(null);

  const toList = useMutation({
    mutationFn: (ids: number[]) =>
      post<RecipeToList>(`/api/recipes/${id}/to-list`, { ingredient_ids: ids }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: keys.list });
      setSelected(new Set());
      setResult(addedMessage(data));
    },
  });
  const remove = useMutation({
    mutationFn: () => del(`/api/recipes/${id}`),
    onSuccess: () => {
      navigate("/recipes");
      queryClient.invalidateQueries({ queryKey: keys.recipes, exact: true });
    },
  });

  if (recipe.isPending) return <p className="muted">Ładowanie…</p>;
  if (recipe.isError) return <p className="error">{errorMessage(recipe.error)}</p>;
  const data = recipe.data;

  function toggle(ingredientId: number) {
    setResult(null);
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(ingredientId)) next.delete(ingredientId);
      else next.add(ingredientId);
      return next;
    });
  }

  function confirmRemove() {
    if (window.confirm(`Usunąć przepis „${data.name}”?`)) remove.mutate();
  }

  return (
    <>
      <div className={styles.heading}>
        <h2 className={styles.title}>{data.name}</h2>
        <Link className={styles.action} to={`/recipes/${id}/edit`}>
          Edytuj
        </Link>
      </div>
      <p className={styles.meta}>
        {[data.servings, data.created_by && `dodał(a) ${data.created_by}`]
          .filter(Boolean)
          .join(" · ")}
        {data.source_url && (
          <>
            {data.servings || data.created_by ? " · " : ""}
            <a href={data.source_url} target="_blank" rel="noopener noreferrer">
              źródło
            </a>
          </>
        )}
      </p>
      <section className="card">
        <h3 className={styles.section}>Składniki</h3>
        <p className={styles.meta}>Zaznacz, czego brakuje w domu.</p>
        <ul className={styles.rows} aria-label="Składniki">
          {data.ingredients.map((ingredient) => (
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
            toList.mutate(data.ingredients.filter((i) => selected.has(i.id)).map((i) => i.id))
          }
        >
          Dodaj zaznaczone na listę
        </button>
        {result && (
          <p className={styles.result} role="status">
            {result}
          </p>
        )}
        {toList.error && <p className="error">{errorMessage(toList.error)}</p>}
      </section>
      {data.instructions && (
        <section className="card">
          <h3 className={styles.section}>Przygotowanie</h3>
          <p className={styles.instructions}>{data.instructions}</p>
        </section>
      )}
      <div>
        <button className="danger" onClick={confirmRemove} disabled={remove.isPending}>
          Usuń przepis
        </button>
        {remove.error && <p className="error">{errorMessage(remove.error)}</p>}
      </div>
    </>
  );
}

interface Row {
  key: number;
  name: string;
  amount: string;
  unit: Unit | "";
  note: string;
  // Kategorię podaje czat; formularz jej nie pokazuje, ale zachowuje przy edycji.
  category: Category | null;
}

let nextRowKey = 0;

function emptyRow(): Row {
  return { key: nextRowKey++, name: "", amount: "", unit: "", note: "", category: null };
}

function toRow(ingredient: RecipeIngredient): Row {
  return {
    key: nextRowKey++,
    name: ingredient.name,
    amount: ingredient.amount === null ? "" : String(ingredient.amount).replace(".", ","),
    unit: ingredient.unit ?? "",
    note: ingredient.note ?? "",
    category: ingredient.category,
  };
}

/** Ilość wpisana z przecinkiem lub kropką; pusta albo niepoprawna — brak ilości. */
export function parseAmount(text: string): number | null {
  const value = Number(text.trim().replace(",", "."));
  return text.trim() !== "" && Number.isFinite(value) && value > 0 ? value : null;
}

function RecipeEditor({ initial }: { initial?: Recipe }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState(initial?.name ?? "");
  const [servings, setServings] = useState(initial?.servings ?? "");
  const [sourceUrl, setSourceUrl] = useState(initial?.source_url ?? "");
  const [instructions, setInstructions] = useState(initial?.instructions ?? "");
  const [rows, setRows] = useState<Row[]>(() =>
    initial ? initial.ingredients.map(toRow) : [emptyRow(), emptyRow(), emptyRow()],
  );
  const [problem, setProblem] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (input: RecipeInput) =>
      initial
        ? put<Recipe>(`/api/recipes/${initial.id}`, input)
        : post<Recipe>("/api/recipes", input),
    onSuccess: (recipe) => {
      queryClient.setQueryData([...keys.recipes, recipe.id], recipe);
      queryClient.invalidateQueries({ queryKey: keys.recipes, exact: true });
      navigate(`/recipes/${recipe.id}`);
    },
  });

  function update(key: number, changes: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...changes } : row)));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const ingredients = rows
      .filter((row) => row.name.trim())
      .map((row) => {
        const amount = parseAmount(row.amount);
        return {
          name: row.name.trim(),
          amount,
          unit: amount === null || row.unit === "" ? null : row.unit,
          note: row.note.trim() || null,
          category: row.category,
        };
      });
    if (!name.trim()) return setProblem("Podaj nazwę przepisu.");
    if (ingredients.length === 0) return setProblem("Dodaj co najmniej jeden składnik.");
    setProblem(null);
    save.mutate({
      name: name.trim(),
      servings: servings.trim() || null,
      source_url: sourceUrl.trim() || null,
      instructions: instructions.trim() || null,
      ingredients,
    });
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <h2 className={styles.title}>{initial ? "Edycja przepisu" : "Nowy przepis"}</h2>
      <label className={styles.field}>
        Nazwa
        <input value={name} maxLength={100} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className={styles.field}>
        Porcje
        <input
          value={servings}
          maxLength={50}
          placeholder="np. 4 porcje"
          onChange={(e) => setServings(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Link do przepisu
        <input
          type="url"
          value={sourceUrl}
          maxLength={2000}
          placeholder="https://…"
          onChange={(e) => setSourceUrl(e.target.value)}
        />
      </label>
      <fieldset className={styles.ingredients}>
        <legend>Składniki</legend>
        <p className={styles.meta}>
          Miary kuchenne (łyżka, szklanka) wpisz w notatce — ilość z jednostką tylko dla szt, kg,
          g, l, ml i opak.
        </p>
        {rows.map((row, index) => (
          <div key={row.key} className={styles.ingredientRow}>
            <input
              aria-label={`Składnik ${index + 1}`}
              placeholder="składnik"
              value={row.name}
              maxLength={100}
              onChange={(e) => update(row.key, { name: e.target.value })}
            />
            <input
              aria-label={`Ilość ${index + 1}`}
              placeholder="ilość"
              inputMode="decimal"
              value={row.amount}
              onChange={(e) => update(row.key, { amount: e.target.value })}
            />
            <select
              aria-label={`Jednostka ${index + 1}`}
              value={row.unit}
              onChange={(e) => update(row.key, { unit: e.target.value as Unit | "" })}
            >
              <option value="">—</option>
              {UNITS.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
            <input
              aria-label={`Notatka ${index + 1}`}
              placeholder="np. 2 łyżki"
              value={row.note}
              maxLength={200}
              onChange={(e) => update(row.key, { note: e.target.value })}
            />
            <button
              type="button"
              aria-label={`Usuń składnik ${index + 1}`}
              onClick={() => setRows((current) => current.filter((r) => r.key !== row.key))}
            >
              ✕
            </button>
          </div>
        ))}
        <button type="button" onClick={() => setRows((current) => [...current, emptyRow()])}>
          Dodaj składnik
        </button>
      </fieldset>
      <label className={styles.field}>
        Przygotowanie
        <textarea
          rows={6}
          value={instructions}
          maxLength={8000}
          onChange={(e) => setInstructions(e.target.value)}
        />
      </label>
      {(problem || save.error) && <p className="error">{problem ?? errorMessage(save.error)}</p>}
      <div className={styles.buttons}>
        <button className="primary" type="submit" disabled={save.isPending}>
          Zapisz przepis
        </button>
        <Link to={initial ? `/recipes/${initial.id}` : "/recipes"}>Anuluj</Link>
      </div>
    </form>
  );
}

function RecipeEdit({ id }: { id: number }) {
  const recipe = useRecipe(id);
  if (recipe.isPending) return <p className="muted">Ładowanie…</p>;
  if (recipe.isError) return <p className="error">{errorMessage(recipe.error)}</p>;
  return <RecipeEditor key={recipe.data.id} initial={recipe.data} />;
}

/** Przepisy gospodarstwa: `/recipes`, `/recipes/new`, `/recipes/:id`, `/recipes/:id/edit`. */
export function RecipesPage() {
  const isNew = useMatch("/recipes/new");
  const edit = useMatch("/recipes/:id/edit");
  const detail = useMatch("/recipes/:id");

  let content;
  let back = { to: "/recipes", label: "← Wszystkie przepisy" };
  if (isNew) content = <RecipeEditor />;
  else if (edit) content = <RecipeEdit id={Number(edit.params.id)} />;
  else if (detail) content = <RecipeDetail key={detail.params.id} id={Number(detail.params.id)} />;
  else {
    content = <RecipeList />;
    back = { to: "/", label: "← Wróć do listy" };
  }

  return (
    <main className={styles.page}>
      <Link to={back.to}>{back.label}</Link>
      {content}
    </main>
  );
}
