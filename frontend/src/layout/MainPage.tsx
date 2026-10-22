import { useState } from "react";
import { Link } from "react-router-dom";
import { ChatView } from "../chat/ChatView";
import { ListView } from "../list/ListView";
import type { Profile } from "../api/types";
import { InstallBanner } from "./InstallBanner";
import styles from "./MainPage.module.css";

type Tab = "chat" | "list";

export function MainPage({ profile, onLogout }: { profile: Profile; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1>Kupto</h1>
        <nav>
          <Link to="/household">{profile.household?.name}</Link>
          <span className="muted">{profile.login}</span>
          <button onClick={onLogout}>Wyloguj</button>
        </nav>
      </header>
      <div className={styles.tabs} role="tablist">
        {(["chat", "list"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
            {t === "chat" ? "Czat" : "Lista"}
          </button>
        ))}
      </div>
      <InstallBanner />
      <main className={styles.content}>
        {/* Na telefonie widoczna jest jedna zakładka, na desktopie obie kolumny. */}
        <div className={`${styles.panel} ${tab === "chat" ? "" : styles.hidden}`}>
          <ChatView />
        </div>
        <div className={`${styles.panel} ${tab === "list" ? "" : styles.hidden}`}>
          <ListView userId={profile.id} />
        </div>
      </main>
    </div>
  );
}
