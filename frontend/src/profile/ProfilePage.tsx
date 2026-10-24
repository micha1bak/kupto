import { useState } from "react";
import { Link } from "react-router-dom";
import type { Profile } from "../api/types";
import { EmailSection } from "../account/EmailSection";
import { NameForm } from "./NameForm";
import styles from "./ProfilePage.module.css";

/** Linki przeniesione z paska nawigacji (spec: app-navigation — „Strona profilu”). */
const LINKS = [
  { to: "/household", label: "Gospodarstwo", hint: "Domownicy, preferencje, powiadomienia" },
  { to: "/history", label: "Historia zakupów", hint: null },
  { to: "/recipes", label: "Przepisy", hint: null },
  { to: "/meal-plan", label: "Plan obiadów", hint: null },
] as const;

export function ProfilePage({ profile, onLogout }: { profile: Profile; onLogout: () => Promise<void> }) {
  const [loggingOut, setLoggingOut] = useState(false);

  async function logout() {
    setLoggingOut(true);
    try {
      await onLogout();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <main className={styles.page}>
      <Link to="/">← Wróć do listy</Link>
      <section className={`card ${styles.who}`}>
        <h2>{profile.name ?? profile.login}</h2>
        {profile.household && <p className="muted">Gospodarstwo „{profile.household.name}”</p>}
      </section>
      <EmailSection profile={profile} />
      <section className={`card ${styles.name}`}>
        <h3>Imię</h3>
        <p className="muted">Widzą je domownicy w czacie i w powiadomieniach.</p>
        <NameForm initial={profile.name ?? ""} submitLabel="Zmień imię" />
      </section>
      <nav aria-label="Profil">
        <ul className={styles.links}>
          {LINKS.map((link) => (
            <li key={link.to}>
              <Link to={link.to}>
                <span>{link.label}</span>
                {link.hint && <span className="muted">{link.hint}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <button className="danger" onClick={logout} disabled={loggingOut}>
        Wyloguj
      </button>
    </main>
  );
}
