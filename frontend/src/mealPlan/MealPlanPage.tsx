import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, del, put } from "../api/client";
import { keys, useMealPlan, useRecipe, useRecipes } from "../api/queries";
import type { MealPlanDayInput, MealPlanEntry } from "../api/types";
import { IngredientsToList } from "../recipes/IngredientsToList";
import { addDays, mondayOf, shortDate, toDay, weekdayName, weekLabel } from "./dates";
import styles from "./MealPlanPage.module.css";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Brak połączenia z serwerem.";
}

/** „wtorek 27 paź” — opis dnia w nagłówku wiersza i w potwierdzeniach. */
function dayLabel(day: string): string {
  return `${weekdayName(day)} ${shortDate(day)}`;
}

/** Co jest rozwinięte w wierszu dnia: formularz dania albo składniki przepisu. */
type Panel = { day: string; kind: "edit" | "ingredients" } | null;

function DayForm({
  day,
  entry,
  onClose,
}: {
  day: string;
  entry: MealPlanEntry | undefined;
  onClose: () => void;
}) {
  const recipes = useRecipes();
  const queryClient = useQueryClient();
  const [recipeId, setRecipeId] = useState(entry?.recipe_id ? String(entry.recipe_id) : "");
  const [name, setName] = useState(entry?.name ?? "");
  const [problem, setProblem] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (input: MealPlanDayInput) => put<MealPlanEntry>(`/api/meal-plan/${day}`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.mealPlan });
      onClose();
    },
  });

  const recipeName = (id: string) => recipes.data?.find((r) => String(r.id) === id)?.name;

  function chooseRecipe(value: string) {
    // Nazwa podpowiada się z przepisu, ale własnej nazwy dania nie nadpisujemy.
    const next = recipeName(value);
    if (next && (name.trim() === "" || name === recipeName(recipeId))) setName(next);
    setRecipeId(value);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed && !recipeId) return setProblem("Podaj nazwę dania albo wybierz przepis.");
    setProblem(null);
    // Bez nazwy serwer bierze nazwę przepisu.
    save.mutate({ name: trimmed || null, recipe_id: recipeId ? Number(recipeId) : null });
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-label={`Danie na ${dayLabel(day)}`}>
      <label className={styles.field}>
        Przepis
        <select
          value={recipeId}
          disabled={recipes.isPending}
          onChange={(e) => chooseRecipe(e.target.value)}
        >
          <option value="">— bez przepisu —</option>
          {recipes.data?.map((recipe) => (
            <option key={recipe.id} value={recipe.id}>
              {recipe.name}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.field}>
        Danie
        <input
          value={name}
          maxLength={100}
          placeholder="np. zupa pomidorowa"
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      {recipes.isError && <p className="error">{errorMessage(recipes.error)}</p>}
      {(problem || save.error) && <p className="error">{problem ?? errorMessage(save.error)}</p>}
      <div className={styles.actions}>
        <button className="primary" type="submit" disabled={save.isPending}>
          Zapisz
        </button>
        <button type="button" onClick={onClose}>
          Anuluj
        </button>
      </div>
    </form>
  );
}

function DayIngredients({ recipeId }: { recipeId: number }) {
  const recipe = useRecipe(recipeId);
  if (recipe.isPending) return <p className="muted">Ładowanie…</p>;
  if (recipe.isError) return <p className="error">{errorMessage(recipe.error)}</p>;
  return (
    <div className={styles.ingredients}>
      <IngredientsToList recipe={recipe.data} />
    </div>
  );
}

function DayRow({
  day,
  entry,
  isToday,
  panel,
  onPanel,
}: {
  day: string;
  entry: MealPlanEntry | undefined;
  isToday: boolean;
  panel: Panel;
  onPanel: (panel: Panel) => void;
}) {
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => del(`/api/meal-plan/${day}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.mealPlan }),
  });
  const open = panel?.day === day ? panel.kind : null;
  const label = dayLabel(day);

  function confirmRemove() {
    if (entry && window.confirm(`Usunąć „${entry.name}” z planu na ${label}?`)) {
      onPanel(null);
      remove.mutate();
    }
  }

  return (
    <li className={isToday ? `${styles.day} ${styles.today}` : styles.day} aria-label={label}>
      <div className={styles.date}>
        <span className={styles.weekday}>{weekdayName(day)}</span>
        <span className={styles.meta}>
          {shortDate(day)}
          {isToday && " · dziś"}
        </span>
      </div>
      {open === "edit" ? (
        <DayForm day={day} entry={entry} onClose={() => onPanel(null)} />
      ) : entry ? (
        <>
          <div className={styles.dish}>
            {entry.recipe_id ? (
              <Link to={`/recipes/${entry.recipe_id}`} className={styles.name}>
                {entry.name}
              </Link>
            ) : (
              <span className={styles.name}>{entry.name}</span>
            )}
            {entry.planned_by && (
              <span className={styles.meta}>zaplanował(a) {entry.planned_by}</span>
            )}
          </div>
          <div className={styles.actions}>
            {entry.recipe_id && (
              <button
                aria-expanded={open === "ingredients"}
                onClick={() => onPanel(open === "ingredients" ? null : { day, kind: "ingredients" })}
              >
                Dodaj brakujące składniki
              </button>
            )}
            <button onClick={() => onPanel({ day, kind: "edit" })}>Zmień</button>
            <button className="danger" onClick={confirmRemove} disabled={remove.isPending}>
              Usuń
            </button>
          </div>
          {open === "ingredients" && entry.recipe_id && (
            <DayIngredients recipeId={entry.recipe_id} />
          )}
        </>
      ) : (
        <div className={styles.actions}>
          <button onClick={() => onPanel({ day, kind: "edit" })}>Dodaj danie</button>
        </div>
      )}
      {remove.error && <p className="error">{errorMessage(remove.error)}</p>}
    </li>
  );
}

/** Kalendarz obiadów: dwa tygodnie od poniedziałku jako pionowa lista dni (`/meal-plan`). */
export function MealPlanPage() {
  const today = toDay(new Date());
  const currentMonday = mondayOf(today);
  const [monday, setMonday] = useState(currentMonday);
  const [panel, setPanel] = useState<Panel>(null);
  const plan = useMealPlan(monday, addDays(monday, 13));

  function showWeek(next: string) {
    setPanel(null);
    setMonday(next);
  }

  const entries = new Map(plan.data?.map((entry) => [entry.day, entry]));
  const weeks = [monday, addDays(monday, 7)];

  return (
    <main className={styles.page}>
      <Link to="/recipes">← Przepisy</Link>
      <h2 className={styles.title}>Plan obiadów</h2>
      <nav className={styles.weeks} aria-label="Tygodnie">
        <button onClick={() => showWeek(addDays(monday, -7))}>← Wcześniej</button>
        {monday !== currentMonday && (
          <button onClick={() => showWeek(currentMonday)}>Ten tydzień</button>
        )}
        <button onClick={() => showWeek(addDays(monday, 7))}>Później →</button>
      </nav>
      {plan.isPending ? (
        <p className="muted">Ładowanie…</p>
      ) : plan.isError ? (
        <p className="error">{errorMessage(plan.error)}</p>
      ) : (
        weeks.map((week) => (
          <section key={week} className="card" aria-label={`Tydzień ${weekLabel(week)}`}>
            <h3 className={styles.section}>{weekLabel(week)}</h3>
            <ul className={styles.days}>
              {Array.from({ length: 7 }, (_, i) => addDays(week, i)).map((day) => (
                <DayRow
                  key={day}
                  day={day}
                  entry={entries.get(day)}
                  isToday={day === today}
                  panel={panel}
                  onPanel={setPanel}
                />
              ))}
            </ul>
          </section>
        ))
      )}
    </main>
  );
}
