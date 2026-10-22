# Tasks

## 1. Backend: wyliczanie kolejności

- [x] 1.1 Dodać do `kupto.lists.ordering` czystą funkcję `learned(base, scores)` (design D4); weryfikacja: testy jednostkowe — brak wyników (kolejność bazowa), wyuczone zamieniają się miejscami, niewyuczone zostają na miejscach, remis wg bazy, wyniki spoza bazy pomijane
- [x] 1.2 Dodać moduł `kupto.lists.learned_order`: odczyt przejść z historii gospodarstwa (własne, potem gospodarstwa — D1–D2) i czyste wyliczenie wyników kategorii i produktów (mediana względnego miejsca, min. 2 obserwacje — D3); weryfikacja: testy jednostkowe wyliczenia oraz testy serwisu dla scenariuszy „Kolejność z własnych odhaczeń”, „Zimny start…”, „Jedno nietypowe przejście…”, „Historia innego gospodarstwa”

## 2. Backend: podpięcie do kolejności kategorii i produktów (spec: shopping-list)

- [x] 2.1 `category_order`: kolejność automatyczna = `learned(list(Category), wyniki)`; `get_order` i `pin` używają kolejności wyuczonej; weryfikacja: istniejące testy kolejności kategorii przechodzą, nowy test „Przypięcie ma pierwszeństwo”
- [x] 2.2 `product_order`: kolejność bazowa = `learned(sorted(names), wyniki)`; `ProductOrder` niesie wyniki, `pin` liczy miejsce na kolejności wyuczonej; weryfikacja: istniejące testy przypinania produktów przechodzą, nowe testy „Kolejność produktów z odhaczeń”, „Element bez historii…”, „Przypięty produkt na tle kolejności wyuczonej”
- [x] 2.3 `GET /api/list` i odpowiedzi mutacji liczą naukę raz dla kategorii i produktów; weryfikacja: testy API „Członkowie z różnymi nawykami” i „Odhaczanie nie przestawia listy”

## 3. Integracja

- [x] 3.1 Uruchomić kroki CI lokalnie: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run pytest`, `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`; weryfikacja: wszystkie przechodzą

## Workflow follow-up

- Archiwizować po `product-order` (jej wymaganie „Kolejność produktów w kategorii” mówi o kolejności bazowej „obecnie alfabetycznej”; po archiwizacji obu zmian doprecyzować je odwołaniem do kolejności wyuczonej).
- Ręcznie sprawdzić na produkcji po kilku zakończeniach zakupów, czy kolejność odpowiada przejściu przez sklep.
