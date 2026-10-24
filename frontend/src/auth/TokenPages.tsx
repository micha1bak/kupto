import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { useAuthConfig } from "../api/queries";
import { MAX_EMAIL_LENGTH, errorText, validateEmail } from "../account/email";
import { MIN_PASSWORD_LENGTH } from "./AuthForm";
import styles from "./AuthForm.module.css";

/**
 * Token z linku w mailu (#77) jest we fragmencie (`#token=…`) — przeglądarka nie wysyła go do
 * serwera, więc nie trafia do logów proxy. Odczytujemy go raz i usuwamy z paska adresu.
 */
function useLinkToken(): string {
  const location = useLocation();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get("token") ?? "");
  useEffect(() => {
    // Bez tokenu w historii przeglądarki (np. na wspólnym komputerze).
    if (token && window.location.hash) {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
  }, [token]);
  return token;
}

const message = (data: { message: string } | undefined) => data?.message ?? "";

/** Strona „Zapomniałem hasła”: odpowiedź nie zdradza, czy konto istnieje. */
export function ForgotPasswordPage() {
  const config = useAuthConfig();
  const [email, setEmail] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const request = useMutation({
    mutationFn: () =>
      post<{ message: string }>("/api/auth/password-reset", { email: email.trim() }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateEmail(email);
    setProblem(invalid);
    if (!invalid) request.mutate();
  }

  const unavailable =
    config.data?.mail_enabled === false ||
    (request.error instanceof ApiError && request.error.code === "mail_unavailable");
  const error = problem ?? (unavailable ? null : errorText(request.error));
  return (
    <main className={styles.page}>
      <form className={`card ${styles.form}`} onSubmit={submit} noValidate>
        <h1>Nowe hasło</h1>
        {unavailable ? (
          <p role="status">
            Wysyłka e-maili jest chwilowo niedostępna, więc nie możemy wysłać linku do zmiany
            hasła. Spróbuj później albo poproś domownika z tego samego gospodarstwa o kontakt z
            administratorem Kupto.
          </p>
        ) : request.isSuccess ? (
          <p role="status">{message(request.data)}</p>
        ) : (
          <>
            <p className="muted">
              Podaj adres e-mail konta — wyślemy link do ustawienia nowego hasła (ważny 30 min).
            </p>
            <label>
              E-mail
              <input
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                maxLength={MAX_EMAIL_LENGTH + 10}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" type="submit" disabled={request.isPending}>
              Wyślij link
            </button>
          </>
        )}
        <p className="muted">
          <Link to="/login">Wróć do logowania</Link>
        </p>
      </form>
    </main>
  );
}

/** Strona z linku resetu hasła: nowe hasło, potem zwykłe logowanie. */
export function ResetPasswordPage() {
  const token = useLinkToken();
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const confirm = useMutation({
    mutationFn: () =>
      post<{ message: string }>("/api/auth/password-reset/confirm", { token, password }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    let invalid: string | null = null;
    if (password.length < MIN_PASSWORD_LENGTH) {
      invalid = `Hasło musi mieć co najmniej ${MIN_PASSWORD_LENGTH} znaków.`;
    } else if (password !== repeat) {
      invalid = "Hasła się różnią.";
    }
    setProblem(invalid);
    if (!invalid) confirm.mutate();
  }

  if (!token) return <BrokenLink title="Nowe hasło" retry="/forgot-password" />;
  const error = problem ?? errorText(confirm.error);
  return (
    <main className={styles.page}>
      <form className={`card ${styles.form}`} onSubmit={submit} noValidate>
        <h1>Nowe hasło</h1>
        {confirm.isSuccess ? (
          <>
            <p role="status">{message(confirm.data)}</p>
            <Link to="/login">Przejdź do logowania</Link>
          </>
        ) : (
          <>
            <label>
              Nowe hasło
              <input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              Powtórz hasło
              <input
                type="password"
                autoComplete="new-password"
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
              />
            </label>
            <p className={`muted ${styles.hint}`}>
              Po zmianie hasła wylogujemy Cię na wszystkich urządzeniach.
            </p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            {confirm.error instanceof ApiError && confirm.error.code === "invalid_token" && (
              <Link to="/forgot-password">Wyślij nowy link</Link>
            )}
            <button className="primary" type="submit" disabled={confirm.isPending}>
              Ustaw hasło
            </button>
          </>
        )}
      </form>
    </main>
  );
}

/**
 * Strona z linku weryfikacyjnego. Potwierdzenie wymaga kliknięcia — skanery linków w poczcie,
 * które otwierają strony same, nie zużyją tokenu. Działa bez logowania (inne urządzenie).
 */
export function VerifyEmailPage() {
  const token = useLinkToken();
  const queryClient = useQueryClient();
  const verify = useMutation({
    mutationFn: () => post<{ message: string }>("/api/auth/verify-email", { token }),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  if (!token) return <BrokenLink title="Potwierdzenie adresu" retry="/profile" />;
  const error = errorText(verify.error);
  return (
    <main className={styles.page}>
      <section className={`card ${styles.form}`}>
        <h1>Potwierdzenie adresu</h1>
        {verify.isSuccess ? (
          <>
            <p role="status">{message(verify.data)}</p>
            <Link to="/">Przejdź do Kupto</Link>
          </>
        ) : (
          <>
            <p className="muted">Potwierdź, że ten adres e-mail należy do Ciebie.</p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            {verify.error instanceof ApiError && verify.error.code === "invalid_token" ? (
              <p className="muted">
                Nowy link wyślesz po zalogowaniu (<Link to="/profile">profil</Link>).
              </p>
            ) : (
              <button
                className="primary"
                onClick={() => verify.mutate()}
                disabled={verify.isPending}
              >
                Potwierdź adres
              </button>
            )}
          </>
        )}
      </section>
    </main>
  );
}

function BrokenLink({ title, retry }: { title: string; retry: string }) {
  return (
    <main className={styles.page}>
      <section className={`card ${styles.form}`}>
        <h1>{title}</h1>
        <p role="alert" className="error">
          Link jest niepełny. Otwórz go jeszcze raz z wiadomości albo poproś o nowy.
        </p>
        <Link to={retry}>Poproś o nowy link</Link>
      </section>
    </main>
  );
}
