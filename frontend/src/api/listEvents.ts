import { useEffect, useRef, useState } from "react";

/** Strumień SSE z sygnałami „lista gospodarstwa się zmieniła” (bez treści listy). */
export const LIST_EVENTS_URL = "/api/list/events";
/** Opóźnienie ponownej próby, gdy przeglądarka zamknęła strumień na dobre (np. 503/409). */
export const RETRY_MIN_MS = 3_000;
export const RETRY_MAX_MS = 60_000;

export interface ListEventsHandlers {
  /** Lista mogła się zmienić — trzeba ją pobrać ponownie. */
  onChange: () => void;
  /** Czy strumień działa (zmiany docierają na żywo), czy trzeba polegać na pollingu. */
  onLiveChange: (live: boolean) => void;
}

/**
 * Połączenie ze strumieniem zmian listy: `EventSource` sam wznawia zerwane połączenie,
 * a gdy zamknie je na dobre (błąd HTTP), próbujemy ponownie z rosnącym opóźnieniem.
 * Karta w tle zamyka strumień; po powrocie lista jest odświeżana i strumień otwierany od nowa.
 */
export class ListEventsConnection {
  private source: EventSource | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private retryDelay = RETRY_MIN_MS;
  private refreshOnReady = false;
  private live = false;
  private running = false;

  constructor(
    private handlers: ListEventsHandlers,
    private doc: Document = document,
  ) {}

  start() {
    if (this.running) return;
    this.running = true;
    this.doc.addEventListener("visibilitychange", this.onVisibilityChange);
    if (!this.doc.hidden) this.connect();
  }

  stop() {
    this.running = false;
    this.doc.removeEventListener("visibilitychange", this.onVisibilityChange);
    this.disconnect();
  }

  private onVisibilityChange = () => {
    if (this.doc.hidden) {
      this.disconnect();
    } else if (!this.source) {
      // Zmiany z czasu, gdy karta była w tle, nie zostaną dosłane — pobieramy listę od razu.
      this.handlers.onChange();
      this.refreshOnReady = false;
      this.connect();
    }
  };

  private connect() {
    this.clearRetry();
    if (typeof EventSource === "undefined") return; // bez wsparcia zostaje polling
    const source = new EventSource(LIST_EVENTS_URL);
    this.source = source;
    source.addEventListener("ready", () => {
      this.retryDelay = RETRY_MIN_MS;
      this.setLive(true);
      // Po ponownym połączeniu mogliśmy przegapić zmiany — strumień ich nie dosyła.
      if (this.refreshOnReady) this.handlers.onChange();
      this.refreshOnReady = false;
    });
    source.addEventListener("list_changed", () => this.handlers.onChange());
    source.onerror = () => {
      this.setLive(false);
      this.refreshOnReady = true;
      if (source.readyState === EventSource.CLOSED) {
        // Serwer odmówił strumienia (np. 409 po usunięciu z gospodarstwa, 503) — pobranie listy
        // od razu pokaże aktualny stan albo przekieruje, zamiast czekać na polling.
        this.handlers.onChange();
        source.close();
        this.source = null;
        this.scheduleRetry();
      }
      // CONNECTING: przeglądarka sama wznowi połączenie (pole `retry` z serwera).
    };
  }

  private disconnect() {
    this.clearRetry();
    this.source?.close();
    this.source = null;
    this.setLive(false);
  }

  private scheduleRetry() {
    if (!this.running || this.doc.hidden) return;
    this.retryTimer = setTimeout(() => this.connect(), this.retryDelay);
    this.retryDelay = Math.min(this.retryDelay * 2, RETRY_MAX_MS);
  }

  private clearRetry() {
    if (this.retryTimer !== null) clearTimeout(this.retryTimer);
    this.retryTimer = null;
  }

  private setLive(live: boolean) {
    if (live === this.live) return;
    this.live = live;
    this.handlers.onLiveChange(live);
  }
}

/** Utrzymuje strumień zmian listy, dopóki komponent jest zamontowany; zwraca, czy działa. */
export function useListEvents(onChange: () => void): boolean {
  const [live, setLive] = useState(false);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    const connection = new ListEventsConnection({
      onChange: () => onChangeRef.current(),
      onLiveChange: setLive,
    });
    connection.start();
    return () => connection.stop();
  }, []);

  return live;
}
