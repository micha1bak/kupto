import { useState } from "react";
import type { Profile } from "../api/types";
import styles from "../profile/ProfilePage.module.css";
import { EmailForm, ResendButton } from "./EmailForm";

/**
 * Blokujący ekran adresu e-mail (#77), gdy serwer wysyła maile:
 * - konto sprzed adresów bez podanego adresu — „Podaj adres e-mail”,
 * - adres niepotwierdzony po terminie — „Potwierdź adres e-mail” z ponownym wysłaniem linku.
 * Po zapisie/kliknięciu linku profil w cache się zmienia, a `App` sam przechodzi dalej.
 */
export function EmailGate({ profile, onLogout }: { profile: Profile; onLogout: () => Promise<void> }) {
  const [loggingOut, setLoggingOut] = useState(false);
  const [changing, setChanging] = useState(false);

  async function logout() {
    setLoggingOut(true);
    try {
      await onLogout();
    } finally {
      setLoggingOut(false);
    }
  }

  const missing = profile.email_status === "missing" || !profile.email;
  return (
    <main className={styles.page}>
      {missing ? (
        <section className="card">
          <h2>Podaj adres e-mail</h2>
          <p className="muted">
            Kupto przechodzi z loginów na adresy e-mail — dzięki temu odzyskasz konto, gdy
            zapomnisz hasła. Wyślemy na ten adres link do potwierdzenia. Do tego czasu logujesz się
            jak dotąd loginem{profile.login ? <> „{profile.login}”</> : null}, a potem adresem.
          </p>
          <EmailForm initial="" submitLabel="Wyślij link" />
        </section>
      ) : (
        <section className="card">
          <h2>Potwierdź adres e-mail</h2>
          <p className="muted">
            Minął termin potwierdzenia adresu <strong>{profile.email}</strong>. Otwórz link z
            wiadomości od Kupto (sprawdź też spam) — potem wrócisz do listy.
          </p>
          <ResendButton email={profile.email!} />
          {changing ? (
            <EmailForm initial={profile.email ?? ""} submitLabel="Zmień adres" />
          ) : (
            <button onClick={() => setChanging(true)}>To nie mój adres</button>
          )}
        </section>
      )}
      <button onClick={logout} disabled={loggingOut}>
        Wyloguj
      </button>
    </main>
  );
}
