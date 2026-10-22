/** Atrapa EventSource: testy wywołują zdarzenia serwera i błędy połączenia. */
export class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];

  readyState = FakeEventSource.CONNECTING;
  onerror: ((event: Event) => void) | null = null;
  private listeners = new Map<string, Array<(event: MessageEvent) => void>>();

  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }

  static get last() {
    return FakeEventSource.instances[FakeEventSource.instances.length - 1];
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }

  emit(type: string) {
    if (type === "ready") this.readyState = FakeEventSource.OPEN;
    for (const listener of this.listeners.get(type) ?? []) listener(new MessageEvent(type, { data: "{}" }));
  }

  /** Zerwanie połączenia: `closed` — przeglądarka nie wznowi go sama (np. odpowiedź 503). */
  fail({ closed = false } = {}) {
    this.readyState = closed ? FakeEventSource.CLOSED : FakeEventSource.CONNECTING;
    this.onerror?.(new Event("error"));
  }
}
