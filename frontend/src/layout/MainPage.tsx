import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChatView } from "../chat/ChatView";
import { chatTitle } from "../chat/chatTitle";
import { ListView } from "../list/ListView";
import type { Profile } from "../api/types";
import { ChatOptions } from "./ChatOptions";
import { InstallBanner } from "./InstallBanner";
import styles from "./MainPage.module.css";

type Tab = "chat" | "list";

function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" focusable="false">
      <circle cx="12" cy="8.5" r="4" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M4.5 20c1.2-3.6 4.2-5.5 7.5-5.5s6.3 1.9 7.5 5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function MainPage({ profile }: { profile: Profile }) {
  const [tab, setTab] = useState<Tab>("chat");
  const [optionsOpen, setOptionsOpen] = useState(false);
  // Zwiększany po wyczyszczeniu historii — nowy czat nie ma lokalnych dymków poprzedniej rozmowy.
  const [chatEpoch, setChatEpoch] = useState(0);
  const titleButton = useRef<HTMLButtonElement>(null);
  const title = chatTitle(profile);

  function closeOptions() {
    setOptionsOpen(false);
    titleButton.current?.focus();
  }

  return (
    <div className={styles.shell}>
      {/* Tylko trzy elementy (spec: app-navigation); reszta jest na profilu i w opcjach czatu. */}
      <header className={styles.header}>
        <Link to="/" className={styles.brand}>
          Kupto
        </Link>
        <button
          ref={titleButton}
          className={styles.chatTitle}
          aria-haspopup="dialog"
          aria-expanded={optionsOpen}
          title={title}
          onClick={() => setOptionsOpen(true)}
        >
          <span className={styles.titleText}>{title}</span>
          <span className={styles.caret} aria-hidden="true">
            ▾
          </span>
        </button>
        <Link to="/profile" className={styles.profile} aria-label="Profil">
          <ProfileIcon />
        </Link>
      </header>
      {optionsOpen && (
        <ChatOptions
          title={title}
          onClose={closeOptions}
          onCleared={() => setChatEpoch((e) => e + 1)}
        />
      )}
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
          <ChatView key={chatEpoch} />
        </div>
        <div className={`${styles.panel} ${tab === "list" ? "" : styles.hidden}`}>
          <ListView userId={profile.id} />
        </div>
      </main>
    </div>
  );
}
