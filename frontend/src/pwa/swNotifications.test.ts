import { describe, expect, it } from "vitest";
import { parsePushPayload, pickWindow, resolveClickUrl } from "./swNotifications";

const ORIGIN = "https://kupto.example";

describe("parsePushPayload", () => {
  it("odczytuje ładunek z backendu", () => {
    const text = JSON.stringify({
      type: "shopping_started",
      title: "Zakupy",
      body: "ala idzie do sklepu",
      url: "/household",
      tag: "shopping",
    });
    expect(parsePushPayload(text)).toEqual({
      type: "shopping_started",
      title: "Zakupy",
      body: "ala idzie do sklepu",
      url: "/household",
      tag: "shopping",
    });
  });

  it.each([null, "", "nie json", "42", '{"title": 5}'])(
    "uszkodzony ładunek %j daje ogólne powiadomienie",
    (text) => {
      expect(parsePushPayload(text)).toMatchObject({ title: "Kupto", url: "/", tag: null });
    },
  );
});

describe("resolveClickUrl", () => {
  it("rozwiązuje ścieżkę względem aplikacji", () => {
    expect(resolveClickUrl("/household", ORIGIN)).toBe(`${ORIGIN}/household`);
    expect(resolveClickUrl(undefined, ORIGIN)).toBe(`${ORIGIN}/`);
  });

  it("nie otwiera innych domen", () => {
    expect(resolveClickUrl("https://evil.example/", ORIGIN)).toBe(`${ORIGIN}/`);
    expect(resolveClickUrl("//evil.example/x", ORIGIN)).toBe(`${ORIGIN}/`);
  });
});

describe("pickWindow", () => {
  it("woli okno na docelowym adresie, inaczej pierwsze otwarte", () => {
    const a = { url: `${ORIGIN}/` };
    const b = { url: `${ORIGIN}/household` };
    expect(pickWindow([a, b], `${ORIGIN}/household`)).toBe(b);
    expect(pickWindow([a, b], `${ORIGIN}/inne`)).toBe(a);
    expect(pickWindow([], `${ORIGIN}/`)).toBeUndefined();
  });
});
