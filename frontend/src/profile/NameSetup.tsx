import { useState } from "react";
import { NameForm } from "./NameForm";
import styles from "./ProfilePage.module.css";

/**
 * Blokujący ekran dla kont sprzed czatu grupowego (#78): bez imienia aplikacja jest niedostępna.
 * Po zapisie profil w cache ma już imię, więc `App` sam przechodzi dalej.
 */
export function NameSetup({ onLogout }: { onLogout: () => Promise<void> }) {
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
      <section className="card">
        <h2>Jak masz na imię?</h2>
        <p className="muted">
          Czat jest teraz wspólny dla całego gospodarstwa — domownicy zobaczą Twoje imię przy
          wiadomościach i w powiadomieniach. Zmienisz je później na stronie profilu.
        </p>
        <NameForm initial="" submitLabel="Zapisz" />
      </section>
      <button onClick={logout} disabled={loggingOut}>
        Wyloguj
      </button>
    </main>
  );
}
