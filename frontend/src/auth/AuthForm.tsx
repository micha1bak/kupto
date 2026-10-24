import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { MAX_EMAIL_LENGTH, validateEmail } from "../account/email";
import { MAX_NAME_LENGTH, validateName } from "../profile/NameForm";
import styles from "./AuthForm.module.css";

type Mode = "login" | "register";

export const MIN_PASSWORD_LENGTH = 8;

function validate(mode: Mode, email: string, password: string, name: string): string | null {
  if (mode === "register") {
    const nameProblem = validateName(name);
    if (nameProblem) return nameProblem;
    const emailProblem = validateEmail(email);
    if (emailProblem) return emailProblem;
    if (password.length < MIN_PASSWORD_LENGTH) {
      return `Hasło musi mieć co najmniej ${MIN_PASSWORD_LENGTH} znaków.`;
    }
  }
  if (!email || !password) return "Podaj adres e-mail i hasło.";
  return null;
}

export function AuthForm({ mode }: { mode: Mode }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = validate(mode, email.trim(), password, name);
    setError(problem);
    if (problem) return;
    setPending(true);
    try {
      // W logowaniu pole przyjmuje też dawny login (konta sprzed #77, do potwierdzenia adresu).
      const credentials = { email: email.trim(), password };
      if (mode === "register") {
        await post("/api/auth/register", { ...credentials, name: name.trim() });
      }
      await post("/api/auth/login", credentials);
      await queryClient.invalidateQueries();
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Brak połączenia z serwerem.");
    } finally {
      setPending(false);
    }
  }

  const isLogin = mode === "login";
  return (
    <main className={styles.page}>
      <form className={`card ${styles.form}`} onSubmit={submit} noValidate>
        <h1>Kupto</h1>
        <p className="muted">
          {isLogin
            ? "Zaloguj się do wspólnej listy."
            : "Załóż konto. Imię zobaczą domownicy we wspólnym czacie, adres e-mail — tylko Ty."}
        </p>
        {!isLogin && (
          <label>
            Imię
            <input
              value={name}
              maxLength={MAX_NAME_LENGTH + 10}
              onChange={(e) => setName(e.target.value)}
              autoComplete="given-name"
            />
          </label>
        )}
        <label>
          E-mail
          <input
            // W logowaniu zwykłe pole tekstowe: przyjmuje też dawny login bez „@”.
            type={isLogin ? "text" : "email"}
            inputMode="email"
            value={email}
            maxLength={MAX_EMAIL_LENGTH + 10}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete={isLogin ? "username" : "email"}
            autoCapitalize="none"
            spellCheck={false}
          />
        </label>
        {isLogin && (
          <p className={`muted ${styles.hint}`}>Konto sprzed zmiany? Możesz wpisać dawny login.</p>
        )}
        <label>
          Hasło
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="primary" type="submit" disabled={pending}>
          {isLogin ? "Zaloguj" : "Zarejestruj"}
        </button>
        <p className="muted">
          {isLogin ? (
            <>
              <Link to="/forgot-password">Zapomniałem hasła</Link>
              <br />
              Nie masz konta? <Link to="/register">Zarejestruj się</Link>
            </>
          ) : (
            <>
              Masz już konto? <Link to="/login">Zaloguj się</Link>
            </>
          )}
        </p>
      </form>
    </main>
  );
}
