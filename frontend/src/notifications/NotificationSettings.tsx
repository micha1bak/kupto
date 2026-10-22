import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import {
  browserPushEnv,
  disablePush,
  enablePush,
  readPushState,
  type PushEnv,
  type PushState,
} from "../pwa/push";
import { NotificationTypes } from "./NotificationTypes";

const DESCRIPTION: Record<PushState, string> = {
  loading: "Sprawdzanie…",
  unsupported: "Ta przeglądarka nie obsługuje powiadomień.",
  "needs-install":
    "Na iPhonie i iPadzie powiadomienia działają tylko w aplikacji dodanej do ekranu " +
    "początkowego: w Safari stuknij Udostępnij, potem „Do ekranu początkowego”, i otwórz " +
    "Kupto z ikony.",
  unavailable: "Powiadomienia są chwilowo niedostępne.",
  blocked:
    "Powiadomienia są zablokowane dla Kupto. Zezwól na nie w ustawieniach witryny " +
    "w przeglądarce (lub w ustawieniach powiadomień telefonu) i otwórz aplikację ponownie.",
  enabled: "Powiadomienia są włączone na tym urządzeniu.",
  disabled: "Dostawaj na tym urządzeniu powiadomienia o zakupach domowników.",
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Nie udało się zmienić ustawień powiadomień. Spróbuj ponownie.";
}

/** Powiadomienia push na tym urządzeniu (spec: notifications — stan i włączanie). */
export function NotificationSettings({ env: injected }: { env?: PushEnv }) {
  const [env] = useState(() => injected ?? browserPushEnv());
  const [state, setState] = useState<PushState>("loading");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    readPushState(env)
      .then((s) => active && setState(s))
      .catch(() => active && setState("unavailable"));
    return () => {
      active = false;
    };
  }, [env]);

  async function change(action: (env: PushEnv) => Promise<PushState>) {
    setBusy(true);
    setError(null);
    try {
      setState(await action(env));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="notifications-heading">
      <h3 id="notifications-heading">Powiadomienia</h3>
      <p className={state === "enabled" || state === "disabled" ? undefined : "muted"}>
        {DESCRIPTION[state]}
      </p>
      {state === "disabled" && (
        <button className="primary" onClick={() => change(enablePush)} disabled={busy}>
          Włącz powiadomienia
        </button>
      )}
      {state === "enabled" && (
        <button onClick={() => change(disablePush)} disabled={busy}>
          Wyłącz powiadomienia
        </button>
      )}
      {error && <p className="error">{error}</p>}
      {/* Typy tylko tam, gdzie serwer i przeglądarka obsługują powiadomienia (design D5). */}
      {(state === "enabled" || state === "disabled") && <NotificationTypes />}
    </section>
  );
}
