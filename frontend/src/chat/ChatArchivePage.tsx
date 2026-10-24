import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { useChatArchive } from "../api/queries";
import { formatMessageTime } from "./time";
import chat from "./ChatView.module.css";
import styles from "./ChatArchivePage.module.css";

/**
 * Dawna prywatna rozmowa z asystentem sprzed czatu grupowego (#78, D2) — tylko do odczytu,
 * widoczna wyłącznie dla jej autora. Link jest w opcjach czatu, gdy archiwum nie jest puste.
 */
export function ChatArchivePage() {
  const archive = useChatArchive();
  const messages = archive.data ?? [];

  return (
    <main className={styles.page}>
      <Link to="/">← Wróć do listy</Link>
      <h2 className={styles.title}>Moje dawne rozmowy</h2>
      <p className="muted">
        Twoja prywatna rozmowa z asystentem sprzed wspólnego czatu gospodarstwa. Widzisz ją tylko
        Ty; asystent jej już nie bierze pod uwagę.
      </p>
      {archive.isLoading && <p className="muted">Ładowanie…</p>}
      {archive.error && (
        <p className="error">
          {archive.error instanceof ApiError ? archive.error.message : "Brak połączenia z serwerem."}
        </p>
      )}
      {archive.data && messages.length === 0 && <p className="muted">Brak dawnych rozmów.</p>}
      <div className={styles.messages} role="log">
        {messages.map((m) => {
          const time = formatMessageTime(m.created_at);
          const assistant = m.role === "assistant";
          return (
            <div key={m.id} className={`${chat.message} ${assistant ? chat.assistant : chat.mine}`}>
              <div className={chat.meta}>
                <span className={chat.sender}>{assistant ? "Asystent" : "Ty"}</span>
                {time && <time dateTime={m.created_at}>{time}</time>}
              </div>
              <div className={chat.bubble}>{m.content}</div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
