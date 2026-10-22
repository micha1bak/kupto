import type { Mock } from "vitest";
import { ListEventsConnection, LIST_EVENTS_URL, RETRY_MAX_MS, RETRY_MIN_MS } from "./listEvents";
import { FakeEventSource } from "../test/fakeEventSource";

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
  document.dispatchEvent(new Event("visibilitychange"));
}

let onChange: Mock<() => void>;
let onLiveChange: Mock<(live: boolean) => void>;
let connection: ListEventsConnection;

beforeEach(() => {
  vi.useFakeTimers();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
  setHidden(false);
  onChange = vi.fn<() => void>();
  onLiveChange = vi.fn<(live: boolean) => void>();
  connection = new ListEventsConnection({ onChange, onLiveChange });
});

afterEach(() => {
  connection.stop();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const lastLive = () => onLiveChange.mock.calls.at(-1)?.[0];

test("is live after ready and reports list changes", () => {
  connection.start();
  expect(FakeEventSource.last.url).toBe(LIST_EVENTS_URL);
  expect(lastLive()).toBeUndefined();

  FakeEventSource.last.emit("ready");
  expect(lastLive()).toBe(true);
  expect(onChange).not.toHaveBeenCalled(); // pierwsze połączenie — listę pobiera zwykłe zapytanie

  FakeEventSource.last.emit("list_changed");
  expect(onChange).toHaveBeenCalledTimes(1);
});

test("refetches the list after the browser reconnects a dropped stream", () => {
  connection.start();
  const source = FakeEventSource.last;
  source.emit("ready");

  source.fail();
  expect(lastLive()).toBe(false);
  expect(FakeEventSource.instances).toHaveLength(1); // wznawia sama przeglądarka

  source.emit("ready");
  expect(lastLive()).toBe(true);
  expect(onChange).toHaveBeenCalledTimes(1);
});

test("retries a closed stream with growing delay up to the maximum", () => {
  connection.start();
  FakeEventSource.last.fail({ closed: true });
  expect(onLiveChange).not.toHaveBeenCalled();

  let delay = RETRY_MIN_MS;
  for (let attempt = 2; attempt <= 8; attempt++) {
    vi.advanceTimersByTime(delay - 1);
    expect(FakeEventSource.instances).toHaveLength(attempt - 1);
    vi.advanceTimersByTime(1);
    expect(FakeEventSource.instances).toHaveLength(attempt);
    FakeEventSource.last.fail({ closed: true });
    delay = Math.min(delay * 2, RETRY_MAX_MS);
  }
  expect(delay).toBe(RETRY_MAX_MS);

  vi.advanceTimersByTime(RETRY_MAX_MS);
  FakeEventSource.last.emit("ready");
  expect(lastLive()).toBe(true);
  // Lista pobierana po każdej odmowie strumienia (8) i po ponownym połączeniu (1).
  expect(onChange).toHaveBeenCalledTimes(9);

  // Po udanym połączeniu opóźnienie wraca do minimum.
  FakeEventSource.last.fail({ closed: true });
  const count = FakeEventSource.instances.length;
  vi.advanceTimersByTime(RETRY_MIN_MS);
  expect(FakeEventSource.instances).toHaveLength(count + 1);
});

test("closes the stream in the background and refreshes on return", () => {
  connection.start();
  const source = FakeEventSource.last;
  source.emit("ready");

  setHidden(true);
  expect(source.readyState).toBe(FakeEventSource.CLOSED);
  expect(lastLive()).toBe(false);

  setHidden(false);
  expect(onChange).toHaveBeenCalledTimes(1);
  expect(FakeEventSource.instances).toHaveLength(2);
  FakeEventSource.last.emit("ready");
  expect(onChange).toHaveBeenCalledTimes(1); // już odświeżona przy powrocie
});

test("does not retry while the tab is hidden", () => {
  connection.start();
  setHidden(true);
  vi.advanceTimersByTime(RETRY_MAX_MS * 2);
  expect(FakeEventSource.instances).toHaveLength(1);
});

test("stop closes the stream and cancels retries", () => {
  connection.start();
  const source = FakeEventSource.last;
  source.fail({ closed: true });
  connection.stop();

  vi.advanceTimersByTime(RETRY_MAX_MS);
  expect(FakeEventSource.instances).toHaveLength(1);
  setHidden(false);
  expect(onChange).toHaveBeenCalledTimes(1); // tylko po odmowie strumienia, nie po zatrzymaniu
});

test("without EventSource support it stays on polling and still refreshes on return", () => {
  vi.stubGlobal("EventSource", undefined);
  connection.start();
  expect(onLiveChange).not.toHaveBeenCalled();

  setHidden(true);
  setHidden(false);
  expect(onChange).toHaveBeenCalledTimes(1);
});
