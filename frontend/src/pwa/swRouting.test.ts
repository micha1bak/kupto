import { describe, expect, it } from "vitest";
import { isApiPath, routeRequest } from "./swRouting";

const ORIGIN = "https://kupto.example";
const PRECACHE = new Set(["/", "/assets/index-abc.js", "/assets/index-abc.css", "/icons/icon-192.png"]);

const route = (path: string, { method = "GET", mode = "cors", origin = ORIGIN } = {}) =>
  routeRequest({ url: `${origin}${path}`, method, mode }, ORIGIN, PRECACHE);

describe("routeRequest", () => {
  it.each([
    ["/api/list"],
    ["/api/users/me"],
    ["/api/chat/messages"],
    ["/api"],
    ["/api/list?x=1"],
  ])("nie obsługuje API (%s)", (path) => {
    expect(route(path)).toBe("passthrough");
  });

  it("nie obsługuje strumienia czatu ani logowania (POST)", () => {
    expect(route("/api/chat/messages", { method: "POST" })).toBe("passthrough");
    expect(route("/api/auth/login", { method: "POST" })).toBe("passthrough");
    expect(route("/api/auth/logout", { method: "POST" })).toBe("passthrough");
  });

  it("nie obsługuje nawigacji do API (np. dokumentacji)", () => {
    expect(route("/api/docs", { mode: "navigate" })).toBe("passthrough");
  });

  it("nawigacje w aplikacji idą najpierw do sieci z powłoką w zapasie", () => {
    expect(route("/", { mode: "navigate" })).toBe("navigation");
    expect(route("/household", { mode: "navigate" })).toBe("navigation");
    expect(route("/login?next=/", { mode: "navigate" })).toBe("navigation");
  });

  it("pliki powłoki z listy precache idą z cache", () => {
    expect(route("/assets/index-abc.js")).toBe("cache-first");
    expect(route("/assets/index-abc.css")).toBe("cache-first");
    expect(route("/icons/icon-192.png")).toBe("cache-first");
  });

  it("nie obsługuje plików spoza listy, innych domen i metod innych niż GET", () => {
    expect(route("/assets/index-old.js")).toBe("passthrough");
    expect(route("/assets/index-abc.js", { origin: "https://cdn.example" })).toBe("passthrough");
    expect(route("/", { method: "HEAD" })).toBe("passthrough");
  });
});

describe("isApiPath", () => {
  it("rozpoznaje tylko /api i /api/…", () => {
    expect(isApiPath("/api")).toBe(true);
    expect(isApiPath("/api/list")).toBe(true);
    expect(isApiPath("/apiary")).toBe(false);
    expect(isApiPath("/")).toBe(false);
  });
});
