import { useState, useSyncExternalStore } from "react";
import {
  bannerVariant,
  clearInstallPrompt,
  getInstallPrompt,
  isDismissed,
  isIos,
  isStandalone,
  rememberDismissal,
  subscribeInstallPrompt,
} from "../pwa/install";
import styles from "./InstallBanner.module.css";

function safeLocalStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

/** Zachęta do instalacji aplikacji (spec: pwa — „Kiedy pokazywać baner”, „Treść banera”). */
export function InstallBanner() {
  const installPrompt = useSyncExternalStore(subscribeInstallPrompt, getInstallPrompt);
  const [dismissed, setDismissed] = useState(() => isDismissed(safeLocalStorage(), Date.now()));
  const [standalone] = useState(() => isStandalone(window));
  const [ios] = useState(() => isIos(navigator));

  const variant = bannerVariant({ standalone, dismissed, canPrompt: installPrompt !== null, ios });
  if (!variant) return null;

  function dismiss() {
    rememberDismissal(safeLocalStorage(), Date.now());
    setDismissed(true);
  }

  async function install() {
    if (!installPrompt) return;
    clearInstallPrompt(); // zdarzenia nie można użyć drugi raz
    await installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === "dismissed") dismiss();
  }

  return (
    <aside className={styles.banner} aria-label="Instalacja aplikacji">
      {variant === "prompt" ? (
        <>
          <p>Zainstaluj Kupto na telefonie — otworzysz listę jednym stuknięciem, także w sklepie.</p>
          <button className="primary" onClick={install}>
            Zainstaluj
          </button>
        </>
      ) : (
        <p>
          Dodaj Kupto do ekranu początkowego: stuknij <strong>Udostępnij</strong>, a potem{" "}
          <strong>„Do ekranu początkowego”</strong>. Na iPhonie powiadomienia (wkrótce) działają
          tylko w aplikacji dodanej do ekranu początkowego.
        </p>
      )}
      <button className={styles.close} onClick={dismiss} aria-label="Zamknij">
        ×
      </button>
    </aside>
  );
}
