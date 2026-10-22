import { describe, expect, it } from "vitest";
import { PUBLIC_SHELL_FILES, precacheList, shellVersion } from "./swPlugin";

describe("precacheList", () => {
  it("zawiera dokument, pliki z assets/ i pliki powłoki z public/", () => {
    const list = precacheList(["index.html", "assets/index-b.js", "assets/index-a.css"]);
    expect(list).toEqual(["/", "/assets/index-a.css", "/assets/index-b.js", ...PUBLIC_SHELL_FILES]);
  });

  it("obejmuje manifest i wszystkie ikony z manifestu", () => {
    expect(PUBLIC_SHELL_FILES).toContain("/manifest.webmanifest");
    expect(PUBLIC_SHELL_FILES).toContain("/icons/apple-touch-icon.png");
    expect(PUBLIC_SHELL_FILES).toContain("/icons/icon-maskable-512.png");
  });

  it("nigdy nie zawiera API", () => {
    expect(precacheList(["assets/x.js"]).some((u) => u.startsWith("/api"))).toBe(false);
  });
});

describe("shellVersion", () => {
  it("jest stała dla tego samego buildu i zmienia się przy zmianie plików lub kodu SW", () => {
    const a = shellVersion(["/", "/assets/a.js"], "code");
    expect(shellVersion(["/", "/assets/a.js"], "code")).toBe(a);
    expect(shellVersion(["/", "/assets/b.js"], "code")).not.toBe(a);
    expect(shellVersion(["/", "/assets/a.js"], "code2")).not.toBe(a);
    expect(a).toMatch(/^[0-9a-f]{16}$/);
  });
});
