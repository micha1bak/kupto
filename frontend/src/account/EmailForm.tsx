import { useState, type FormEvent } from "react";
import styles from "../profile/NameForm.module.css";
import { MAX_EMAIL_LENGTH, errorText, useSendVerification, validateEmail } from "./email";

/** Podanie lub zmiana adresu e-mail — serwer wysyła na niego link weryfikacyjny. */
export function EmailForm({ initial, submitLabel }: { initial: string; submitLabel: string }) {
  const [email, setEmail] = useState(initial);
  const [problem, setProblem] = useState<string | null>(null);
  const send = useSendVerification();

  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateEmail(email);
    setProblem(invalid);
    if (!invalid) send.mutate(email);
  }

  const error = problem ?? errorText(send.error);
  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <input
        aria-label="Adres e-mail"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={email}
        maxLength={MAX_EMAIL_LENGTH + 10}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button className="primary" type="submit" disabled={send.isPending}>
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

/** (Ponowne) wysłanie linku na adres czekający na potwierdzenie. */
export function ResendButton({
  email,
  label = "Wyślij link ponownie",
}: {
  email: string;
  label?: string;
}) {
  const send = useSendVerification();
  const error = errorText(send.error);
  return (
    <>
      <button onClick={() => send.mutate(email)} disabled={send.isPending || send.isSuccess}>
        {send.isSuccess ? "Wysłano" : label}
      </button>
      {send.isSuccess && (
        <p className="muted" role="status">
          Wysłaliśmy link na {email}. Wcześniejsze linki przestały działać.
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
