import { Link } from "react-router-dom";
import type { Profile } from "../api/types";
import styles from "../layout/InstallBanner.module.css";
import { formatDeadline } from "./email";
import { ResendButton } from "./EmailForm";

/** Przypomnienie o potwierdzeniu adresu w terminie (#77); po terminie — `EmailGate`. */
export function EmailBanner({ profile }: { profile: Profile }) {
  if (!profile.mail_enabled || profile.email_status !== "unverified" || !profile.email) return null;
  if (profile.email_blocked) return null;
  // Bez terminu: konto założone, gdy wysyłka nie działała — link nie został jeszcze wysłany.
  const sent = profile.verify_email_by !== null;
  return (
    <aside className={styles.banner} aria-label="Potwierdzenie adresu e-mail">
      <p>
        {sent ? (
          <>
            Potwierdź adres <strong>{profile.email}</strong> linkiem z wiadomości (do{" "}
            {formatDeadline(profile.verify_email_by!)}).
          </>
        ) : (
          <>
            Potwierdź adres <strong>{profile.email}</strong> — wyślemy na niego link.
          </>
        )}{" "}
        <Link to="/profile">Zmień adres</Link>
      </p>
      <ResendButton email={profile.email} label={sent ? "Wyślij link ponownie" : "Wyślij link"} />
    </aside>
  );
}
