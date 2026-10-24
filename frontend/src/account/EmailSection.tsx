import type { Profile } from "../api/types";
import styles from "../profile/ProfilePage.module.css";
import { formatDeadline } from "./email";
import { EmailForm, ResendButton } from "./EmailForm";

/** Adres e-mail na stronie profilu (#77) — widzi go tylko właściciel konta. */
export function EmailSection({ profile }: { profile: Profile }) {
  const { email, email_status: status, mail_enabled: mailEnabled } = profile;
  return (
    <section className={`card ${styles.name}`}>
      <h3>Adres e-mail</h3>
      {status === "verified" && (
        <p className="muted">
          <strong>{email}</strong> — potwierdzony. Logujesz się tym adresem.
        </p>
      )}
      {status === "unverified" && email && (
        <>
          <p className="muted">
            <strong>{email}</strong> — niepotwierdzony. Otwórz link z wiadomości
            {profile.verify_email_by && mailEnabled
              ? ` (do ${formatDeadline(profile.verify_email_by)})`
              : ""}
            .
          </p>
          {mailEnabled && (
            <>
              <ResendButton email={email} />
              <EmailForm initial={email} submitLabel="Zmień adres" />
            </>
          )}
        </>
      )}
      {status === "missing" &&
        (mailEnabled ? (
          <EmailForm initial="" submitLabel="Wyślij link" />
        ) : (
          <p className="muted">Nie podano adresu.</p>
        ))}
      {profile.login && !profile.email_verified && (
        <p className="muted">
          Do potwierdzenia adresu logujesz się loginem „{profile.login}”, potem adresem e-mail.
        </p>
      )}
      {!mailEnabled && status !== "verified" && (
        <p className="muted">
          Wysyłka e-maili jest jeszcze niedostępna — potwierdzenie adresu będzie możliwe później.
        </p>
      )}
    </section>
  );
}
