import indexHtml from "../../index.html?raw";
import globalCss from "../index.css?raw";
import mainPageCss from "./MainPage.module.css?raw";
import listCss from "../list/ListView.module.css?raw";

// Regresja #76: na iPhonie (PWA i Safari) widok nie może wychodzić poza szerokość ekranu.
// jsdom nie liczy układu, więc pilnujemy tu reguł, które do tego prowadziły; scrollWidth przy
// 375 i 430 px sprawdzono ręcznie w przeglądarce.

const allCss = import.meta.glob<string>("../**/*.css", {
  query: "?raw",
  import: "default",
  eager: true,
});

/** Usuwa komentarze, by sprawdzać tylko prawdziwe deklaracje. */
const strip = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");

describe("szerokość widoku na telefonie", () => {
  it("viewport dopasowuje się do ekranu i obejmuje obszar pod notchem", () => {
    const doc = new DOMParser().parseFromString(indexHtml, "text/html");
    const content = doc.querySelector('meta[name="viewport"]')?.getAttribute("content") ?? "";
    const parts = content.split(",").map((part) => part.trim());

    expect(parts).toEqual(
      expect.arrayContaining(["width=device-width", "initial-scale=1", "viewport-fit=cover"]),
    );
    // Bez blokowania powiększania — to tylko szkodzi dostępności.
    expect(content).not.toMatch(/user-scalable|maximum-scale/);
  });

  it("żaden arkusz nie używa 100vw (na iOS daje przewijanie w poziomie)", () => {
    expect(Object.keys(allCss).length).toBeGreaterThan(5);
    for (const [path, css] of Object.entries(allCss)) {
      expect({ path, has100vw: /\b100vw\b/.test(strip(css)) }).toEqual({ path, has100vw: false });
    }
  });

  it("przy viewport-fit=cover treść omija notch i wskaźnik ekranu głównego", () => {
    const css = strip(globalCss) + strip(mainPageCss);
    for (const side of ["left", "right", "top", "bottom"]) {
      expect(css).toContain(`env(safe-area-inset-${side}`);
    }
  });

  it("pola formularzy mają co najmniej 16 px, żeby iOS nie powiększał strony przy fokusie", () => {
    expect(strip(globalCss)).toMatch(/font-size:\s*max\(16px,/);
    for (const [path, css] of Object.entries(allCss)) {
      const small = [...strip(css).matchAll(/(input|select|textarea)[^{}]*\{[^}]*font-size:\s*([^;]+);/g)]
        .map((match) => match[2].trim())
        .filter((size) => !size.startsWith("max(16px"));
      expect({ path, small }).toEqual({ path, small: [] });
    }
  });

  it("pasek nawigacji mieści się w jednym wierszu i skraca długi tytuł czatu (#80)", () => {
    const css = strip(mainPageCss);
    expect(css).toMatch(/\.header \{[^}]*grid-template-columns:\s*auto minmax\(0, 1fr\) auto/);
    expect(css).not.toMatch(/\.header \{[^}]*flex-wrap/);
    expect(css).toMatch(/\.titleText \{[^}]*text-overflow:\s*ellipsis/);
    expect(css).toMatch(/\.titleText \{[^}]*white-space:\s*nowrap/);
    // Ikona profilu: cel dotyku co najmniej 44 × 44 px.
    expect(css).toMatch(/\.profile \{[^}]*width:\s*44px/);
    expect(css).toMatch(/\.profile \{[^}]*height:\s*44px/);
  });

  it("wiersz listy pozwala zawinąć długą nazwę produktu", () => {
    expect(strip(listCss)).toMatch(/\.item \{[^}]*grid-template-columns:\s*auto auto minmax\(0, 1fr\) auto/);
    expect(strip(listCss)).toMatch(/\.name \{[^}]*overflow-wrap:\s*anywhere/);
  });
});
