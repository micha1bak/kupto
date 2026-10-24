import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { keys, useChatHistory } from "../api/queries";
import { streamChat } from "../api/sse";
import styles from "./ChatView.module.css";

const MAX_LENGTH = 8000; // mieści wklejony przepis

interface Bubble {
  key: string;
  role: "user" | "assistant" | "error";
  content: string;
}

export function ChatView() {
  const queryClient = useQueryClient();
  const history = useChatHistory();
  const [local, setLocal] = useState<Bubble[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const stored: Bubble[] = (history.data ?? []).map((m) => ({
    key: `h${m.id}`,
    role: m.role,
    content: m.content,
  }));
  const bubbles = [...stored, ...local];

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [bubbles.length, local]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const content = draft.trim();
    if (!content || sending) return;
    if (content.length > MAX_LENGTH) {
      setLocal((l) => [...l, { key: `e${Date.now()}`, role: "error", content: `Wiadomość może mieć najwyżej ${MAX_LENGTH} znaków.` }]);
      return;
    }
    const id = Date.now();
    const replyKey = `a${id}`;
    setDraft("");
    setSending(true);
    setLocal((l) => [
      ...l.filter((b) => b.role !== "error"),
      { key: `u${id}`, role: "user", content },
      { key: replyKey, role: "assistant", content: "" },
    ]);
    const append = (text: string) =>
      setLocal((l) => l.map((b) => (b.key === replyKey ? { ...b, content: b.content + text } : b)));
    const showError = (message: string) =>
      setLocal((l) => [...l, { key: `e${id}`, role: "error", content: message }]);
    try {
      await streamChat(content, {
        onDelta: append,
        onListChanged: () => queryClient.invalidateQueries({ queryKey: keys.list }),
        onError: showError,
      });
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "Brak połączenia z serwerem.");
    } finally {
      setLocal((l) => l.filter((b) => b.role !== "assistant" || b.content !== ""));
      setSending(false);
      queryClient.invalidateQueries({ queryKey: keys.list });
      // Asystent mógł zapisać przepis (save_recipe) albo zmienić preferencje gospodarstwa
      // (update_preferences) — tego nie sygnalizuje strumień listy.
      queryClient.invalidateQueries({ queryKey: keys.recipes });
      queryClient.invalidateQueries({ queryKey: keys.householdPreferences });
      try {
        // Zapisana historia zawiera już tę wymianę — lokalne dymki zastępujemy wersją z serwera.
        await queryClient.refetchQueries({ queryKey: keys.chat }, { throwOnError: true });
        setLocal((l) => l.filter((b) => b.role === "error"));
      } catch {
        // bez odświeżonej historii zostawiamy lokalne dymki, by nic nie zniknęło
      }
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <section className={styles.view} aria-label="Czat">
      <div className={styles.header}>
        {/* Wyczyszczenie historii jest w opcjach czatu (tytuł czatu w pasku, layout/ChatOptions). */}
        <h2>Asystent</h2>
      </div>
      <div className={styles.messages} role="log" aria-live="polite">
        {bubbles.length === 0 && !history.isLoading && (
          <p className={`muted ${styles.hint}`}>
            Napisz, czego potrzebujesz — np. „skończyło się mleko i chleb” albo „coś na grilla w
            sobotę”. Możesz też wkleić przepis — zapytam, czego brakuje.
          </p>
        )}
        {bubbles.map((b) => (
          <div
            key={b.key}
            className={b.role === "error" ? styles.errorBubble : `${styles.bubble} ${styles[b.role]}`}
            role={b.role === "error" ? "alert" : undefined}
          >
            {b.content || "…"}
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form className={styles.form} onSubmit={send}>
        <textarea
          aria-label="Wiadomość"
          placeholder="Czego potrzebujesz?"
          value={draft}
          rows={1}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button className="primary" type="submit" disabled={sending || !draft.trim()}>
          Wyślij
        </button>
      </form>
      <p className={`muted ${styles.privacy}`}>
        Wiadomości są przetwarzane przez zewnętrzny model językowy w celu aktualizacji listy.
      </p>
    </section>
  );
}
