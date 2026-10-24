import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, del, post } from "../api/client";
import { keys, useHousehold, useProfile } from "../api/queries";
import type { Household } from "../api/types";
import { NotificationSettings } from "../notifications/NotificationSettings";
import { HouseholdPreferences } from "./HouseholdPreferences";
import styles from "./HouseholdPage.module.css";

function errorMessage(error: unknown): string | null {
  if (!error) return null;
  return error instanceof ApiError ? error.message : "Brak połączenia z serwerem.";
}

/** Formularz dla użytkownika bez gospodarstwa. */
export function HouseholdSetup({ login }: { login: string }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("Dom");
  const create = useMutation({
    mutationFn: () => post<Household>("/api/households", { name: name.trim() }),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim()) create.mutate();
  }

  return (
    <main className={styles.page}>
      <section className="card">
        <h2>Utwórz gospodarstwo</h2>
        <p className="muted">
          Gospodarstwo to grupa domowników ze wspólną listą zakupów.
        </p>
        <form className={styles.inline} onSubmit={submit}>
          <input
            aria-label="Nazwa gospodarstwa"
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="primary" type="submit" disabled={create.isPending}>
            Utwórz
          </button>
        </form>
        {create.error && <p className="error">{errorMessage(create.error)}</p>}
      </section>
      <section className="card">
        <h2>Dołącz do istniejącego</h2>
        <p className="muted">
          Poproś właściciela gospodarstwa, aby dodał Twój login: <strong>{login}</strong>
        </p>
      </section>
    </main>
  );
}

export function HouseholdPage() {
  const queryClient = useQueryClient();
  const profile = useProfile();
  const household = useHousehold();
  const [login, setLogin] = useState("");
  const refresh = () => queryClient.invalidateQueries();

  const addMember = useMutation({
    mutationFn: () => post<Household>("/api/households/me/members", { login: login.trim() }),
    onSuccess: (data) => {
      queryClient.setQueryData(keys.household, data);
      setLogin("");
    },
  });
  const removeMember = useMutation({
    mutationFn: (userId: number) => del<Household>(`/api/households/me/members/${userId}`),
    onSuccess: (data) => queryClient.setQueryData(keys.household, data),
  });
  const leave = useMutation({
    mutationFn: () => post("/api/households/me/leave"),
    onSuccess: refresh,
  });

  if (!household.data || !profile.data) return <p className="muted">Ładowanie…</p>;
  const me = profile.data;
  const isOwner = household.data.members.some((m) => m.id === me.id && m.is_owner);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (login.trim()) addMember.mutate();
  }

  function confirmLeave() {
    const last = household.data!.members.length === 1;
    const warning = last
      ? "Jesteś ostatnim członkiem — gospodarstwo, lista i historia czatu zostaną usunięte. Kontynuować?"
      : "Czy na pewno chcesz opuścić gospodarstwo?";
    if (window.confirm(warning)) leave.mutate();
  }

  return (
    <main className={styles.page}>
      <Link to="/">← Wróć do listy</Link>
      <section className="card">
        <h2>{household.data.name}</h2>
        <ul className={styles.members} aria-label="Członkowie">
          {household.data.members.map((member) => (
            <li key={member.id}>
              <span>
                {member.login}
                {member.is_owner && <span className={styles.badge}>właściciel</span>}
              </span>
              {isOwner && member.id !== me.id && (
                <button
                  className="danger"
                  onClick={() => removeMember.mutate(member.id)}
                  aria-label={`Usuń ${member.login}`}
                >
                  Usuń
                </button>
              )}
            </li>
          ))}
        </ul>
        {removeMember.error && <p className="error">{errorMessage(removeMember.error)}</p>}
      </section>
      {isOwner && (
        <section className="card">
          <h3>Dodaj domownika</h3>
          <form className={styles.inline} onSubmit={submit}>
            <input
              aria-label="Login domownika"
              placeholder="login"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
            />
            <button className="primary" type="submit" disabled={addMember.isPending}>
              Dodaj
            </button>
          </form>
          {addMember.error && <p className="error">{errorMessage(addMember.error)}</p>}
        </section>
      )}
      <HouseholdPreferences />
      <NotificationSettings />
      <button className="danger" onClick={confirmLeave} disabled={leave.isPending}>
        Opuść gospodarstwo
      </button>
    </main>
  );
}
