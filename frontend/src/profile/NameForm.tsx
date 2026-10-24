import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, patch } from "../api/client";
import { keys } from "../api/queries";
import type { Profile } from "../api/types";
import styles from "./NameForm.module.css";

/** Imię widzą domownicy w czacie gospodarstwa i w powiadomieniach (#78). */
export const MAX_NAME_LENGTH = 40;

/** Ta sama reguła co na serwerze: 1–40 znaków po obcięciu spacji. */
export function validateName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) return "Podaj imię.";
  if (trimmed.length > MAX_NAME_LENGTH) return `Imię może mieć najwyżej ${MAX_NAME_LENGTH} znaków.`;
  return null;
}

/** Zapis imienia bieżącego użytkownika (`PATCH /api/users/me`) — profil w cache od razu się zmienia. */
export function NameForm({ initial, submitLabel }: { initial: string; submitLabel: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(initial);
  const [problem, setProblem] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: (value: string) => patch<Profile>("/api/users/me", { name: value }),
    onSuccess: (profile) => {
      queryClient.setQueryData(keys.profile, profile);
      setName(profile.name ?? "");
      // Imię podpisuje wiadomości w czacie — zapisane już wiadomości też się zmieniają.
      queryClient.invalidateQueries({ queryKey: keys.chat });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateName(name);
    setProblem(invalid);
    if (!invalid) save.mutate(name.trim());
  }

  const error =
    problem ??
    (save.error
      ? save.error instanceof ApiError
        ? save.error.message
        : "Brak połączenia z serwerem."
      : null);

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <input
        aria-label="Imię"
        value={name}
        maxLength={MAX_NAME_LENGTH + 10}
        autoComplete="given-name"
        onChange={(e) => setName(e.target.value)}
      />
      <button className="primary" type="submit" disabled={save.isPending || name.trim() === initial}>
        {submitLabel}
      </button>
      {error && (
        <p className={`error ${styles.error}`} role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
