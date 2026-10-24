import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, post } from "../api/client";
import { MAX_NAME_LENGTH, validateName } from "../profile/NameForm";
import styles from "./AuthForm.module.css";

type Mode = "login" | "register";

function validate(mode: Mode, login: string, password: string, name: string): string | null {
  if (mode === "register") {
    const nameProblem = validateName(name);
    if (nameProblem) return nameProblem;
    if (login.length < 3 || login.length > 50) return "Login musi mieć od 3 do 50 znaków.";
    if (password.length < 8) return "Hasło musi mieć co najmniej 8 znaków.";
  }
  if (!login || !password) return "Podaj login i hasło.";
  return null;
}

export function AuthForm({ mode }: { mode: Mode }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [login, setLogin] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const problem = validate(mode, login.trim(), password, name);
    setError(problem);
    if (problem) return;
    setPending(true);
    try {
      const credentials = { login: login.trim(), password };
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
        <p className="muted">{isLogin ? "Zaloguj się do wspólnej listy." : "Załóż konto. Imię zobaczą domownicy we wspólnym czacie."}</p>
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
          Login
          <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" />
        </label>
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
