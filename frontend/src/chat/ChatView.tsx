import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import { onChatChanged } from "../api/listEvents";
import { keys, useChatHistory } from "../api/queries";
import { streamChat } from "../api/sse";
import { formatMessageTime } from "./time";
import styles from "./ChatView.module.css";

const MAX_LENGTH = 8000; // mieści wklejony przepis

interface Bubble {
  key: string;
  role: "user" | "assistant" | "error";
  content: string;
  /** Imię autora wiadomości domownika (dla własnych „Ty”). */
  author?: string;
  mine?: boolean;
  createdAt?: string;
}

/** Kto napisał: własne „Ty” po prawej, domownik z imieniem, asystent wyraźnie oznaczony (#78). */
function senderLabel(bubble: Bubble): string {
  if (bubble.role === "assistant") return "Asystent";
  return bubble.mine ? "Ty" : (bubble.author ?? "Domownik");
}

function bubbleClass(bubble: Bubble): string {
  if (bubble.role === "assistant") return styles.assistant;
  return bubble.mine ? styles.mine : styles.other;
}

export function ChatView() {
  const queryClient = useQueryClient();
  const history = useChatHistory();
  const [local, setLocal] = useState<Bubble[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  // W trakcie własnej wymiany odświeżenie z sygnału czekamy do jej końca (i tak pobieramy wtedy
  // wątek) — inaczej lokalne dymki wymiany pojawiłyby się podwójnie.
  const sendingRef = useRef(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(
    () =>
      onChatChanged(() => {
        if (!sendingRef.current) queryClient.invalidateQueries({ queryKey: keys.chat });
      }),
    [queryClient],
  );

  const stored: Bubble[] = (history.data ?? []).map((m) => ({
    key: `h${m.id}`,
    role: m.role,
    content: m.content,
    author: m.author?.name,
    mine: m.mine,
    createdAt: m.created_at,
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
    sendingRef.current = true;
    const now = new Date().toISOString();
    setLocal((l) => [
      ...l.filter((b) => b.role !== "error"),
      { key: `u${id}`, role: "user", content, mine: true, createdAt: now },
      { key: replyKey, role: "assistant", content: "", createdAt: now },
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
      sendingRef.current = false;
      queryClient.invalidateQueries({ queryKey: keys.list });
      // Asystent mógł zapisać przepis (save_recipe), zmienić preferencje gospodarstwa
      // (update_preferences) albo plan obiadów (save_meal_plan) — tego nie sygnalizuje strumień listy.
      queryClient.invalidateQueries({ queryKey: keys.recipes });
      queryClient.invalidateQueries({ queryKey: keys.householdPreferences });
      queryClient.invalidateQueries({ queryKey: keys.mealPlan });
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
        {/* Ukrycie historii jest w opcjach czatu (tytuł czatu w pasku, layout/ChatOptions). */}
        <h2>Czat gospodarstwa</h2>
      </div>
      <div className={styles.messages} role="log" aria-live="polite">
        {bubbles.length === 0 && !history.isLoading && (
          <p className={`muted ${styles.hint}`}>
            Tu piszą wszyscy domownicy, a asystent odpowiada na każdą wiadomość. Napisz, czego
            potrzebujesz — np. „skończyło się mleko i chleb” albo „coś na grilla w sobotę”. Możesz
            też wkleić przepis — asystent zapyta, czego brakuje.
          </p>
        )}
        {bubbles.map((b) => {
          if (b.role === "error") {
            return (
              <div key={b.key} className={styles.errorBubble} role="alert">
                {b.content}
              </div>
            );
          }
          const time = b.createdAt ? formatMessageTime(b.createdAt) : null;
          return (
            <div key={b.key} className={`${styles.message} ${bubbleClass(b)}`}>
              <div className={styles.meta}>
                <span className={styles.sender}>{senderLabel(b)}</span>
                {time && <time dateTime={b.createdAt}>{time}</time>}
              </div>
              <div className={styles.bubble}>{b.content || "…"}</div>
            </div>
          );
        })}
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
