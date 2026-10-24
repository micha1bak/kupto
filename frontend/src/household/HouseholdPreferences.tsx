import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, put } from "../api/client";
import { keys, useHouseholdPreferences } from "../api/queries";
import type { HouseholdPreferences as Preferences, HouseholdPreferencesInput } from "../api/types";
import styles from "./HouseholdPage.module.css";

const joinItems = (items: string[]) => items.join(", ");
const splitItems = (text: string) =>
  text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
const toNumber = (text: string) => (text.trim() === "" ? null : Number(text));

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Nie udało się zapisać preferencji. Spróbuj ponownie.";
}

/** Preferencje żywieniowe gospodarstwa — wspólne dla domowników, zna je asystent (design D5). */
export function HouseholdPreferences() {
  const queryClient = useQueryClient();
  const preferences = useHouseholdPreferences();
  const save = useMutation({
    mutationFn: (body: HouseholdPreferencesInput) =>
      put<Preferences>("/api/households/me/preferences", body),
    onSuccess: (data) => queryClient.setQueryData(keys.householdPreferences, data),
  });
  const current = preferences.data;
  // „Zapisano” tylko dla wersji, którą zapisał ten formularz (nie po zmianie np. przez czat).
  const saved = save.isSuccess && current?.updated_at === save.data.updated_at;

  return (
    <section className="card" aria-labelledby="preferences-heading">
      <h3 id="preferences-heading">Preferencje</h3>
      <p className="muted">Asystent bierze je pod uwagę, gdy proponuje dania, przepisy i zakupy.</p>
      {current ? (
        // Nowa wersja z serwera (zapis albo zmiana przez czat) wypełnia formularz od nowa.
        <PreferencesForm
          key={current.updated_at ?? "empty"}
          initial={current}
          pending={save.isPending}
          onSave={(body) => save.mutate(body)}
        />
      ) : preferences.error ? (
        <p className="error">Nie udało się wczytać preferencji.</p>
      ) : (
        <p className="muted">Ładowanie…</p>
      )}
      {saved && <p role="status">Zapisano.</p>}
      {save.error && <p className="error">{errorMessage(save.error)}</p>}
      {current?.updated_by && !saved && (
        <p className={styles.hint}>Ostatnio zmieniał(a): {current.updated_by}</p>
      )}
    </section>
  );
}

function PreferencesForm({
  initial,
  pending,
  onSave,
}: {
  initial: Preferences;
  pending: boolean;
  onSave: (body: HouseholdPreferencesInput) => void;
}) {
  const [people, setPeople] = useState(initial.people?.toString() ?? "");
  const [diets, setDiets] = useState(joinItems(initial.diets));
  const [excluded, setExcluded] = useState(joinItems(initial.excluded));
  const [disliked, setDisliked] = useState(joinItems(initial.disliked));
  const [minutes, setMinutes] = useState(initial.max_cooking_minutes?.toString() ?? "");
  const [notes, setNotes] = useState(initial.notes ?? "");

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({
      people: toNumber(people),
      diets: splitItems(diets),
      excluded: splitItems(excluded),
      disliked: splitItems(disliked),
      max_cooking_minutes: toNumber(minutes),
      notes: notes.trim() || null,
    });
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <label className={styles.field}>
        Liczba osób
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={20}
          value={people}
          onChange={(e) => setPeople(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Diety
        <input
          value={diets}
          placeholder="np. wegetariańska, bez glutenu"
          onChange={(e) => setDiets(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Alergie i czego nie jemy
        <input
          value={excluded}
          placeholder="np. orzechy, owoce morza"
          onChange={(e) => setExcluded(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Czego nie lubimy
        <input
          value={disliked}
          placeholder="np. seler, oliwki"
          onChange={(e) => setDisliked(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Maks. czas gotowania (min)
        <input
          type="number"
          inputMode="numeric"
          min={5}
          max={480}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
        />
      </label>
      <label className={styles.field}>
        Inne uwagi
        <textarea
          value={notes}
          maxLength={300}
          rows={2}
          placeholder="np. w tygodniu tanio i szybko"
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      <p className={styles.hint}>Kilka pozycji w polu oddziel przecinkami.</p>
      <button className="primary" type="submit" disabled={pending}>
        Zapisz preferencje
      </button>
    </form>
  );
}
