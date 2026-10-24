import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, del } from "../api/client";
import { keys, useChatHistory } from "../api/queries";
import styles from "./ChatOptions.module.css";

/**
 * Opcje czatu otwierane tytułem czatu w pasku (spec: app-navigation — „Opcje czatu”).
 * Arkusz przy dolnej krawędzi na telefonie, wyśrodkowany na szerokim ekranie.
 */
export function ChatOptions({
  title,
  onClose,
  onCleared,
}: {
  title: string;
  onClose: () => void;
  /** Po ukryciu historii — np. by usunąć lokalne dymki czatu. */
  onCleared: () => void;
}) {
  const queryClient = useQueryClient();
  const history = useChatHistory();
  const panel = useRef<HTMLDivElement>(null);

  const clear = useMutation({
    mutationFn: () => del("/api/chat/messages"),
    onSuccess: () => {
      queryClient.setQueryData(keys.chat, []);
      onCleared();
      onClose();
    },
  });

  // Najświeższe `onClose` bez ponownego podpinania nasłuchu (i ponownego fokusu) przy każdym renderze.
  const close = useRef(onClose);
  close.current = onClose;

  useEffect(() => {
    panel.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") close.current();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  // Czat jest wspólny (#78): wiadomości znikają tylko u siebie, domownicy i asystent widzą je dalej.
  function confirmClear() {
    if (
      window.confirm(
        "Ukryć dotychczasowe wiadomości czatu u siebie? Domownicy nadal je zobaczą, a lista zakupów się nie zmieni.",
      )
    ) {
      clear.mutate();
    }
  }

  const empty = (history.data ?? []).length === 0;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div
        ref={panel}
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-labelledby="chat-options-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.head}>
          <h2 id="chat-options-title">{title}</h2>
          <button className={styles.close} onClick={onClose}>
            Zamknij
          </button>
        </div>
        <p className="muted">Opcje czatu</p>
        <ul className={styles.options}>
          <li>
            <button
              className="danger"
              onClick={confirmClear}
              disabled={empty || clear.isPending}
            >
              Ukryj historię u siebie
            </button>
          </li>
          <li>
            <Link to="/household">Gospodarstwo i domownicy</Link>
          </li>
        </ul>
        {clear.error && (
          <p className="error">
            {clear.error instanceof ApiError ? clear.error.message : "Brak połączenia z serwerem."}
          </p>
        )}
      </div>
    </div>
  );
}
