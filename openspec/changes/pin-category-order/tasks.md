# Tasks

## 1. Backend: model i wyliczanie kolejności

- [x] 1.1 Dodać moduł `kupto.lists.ordering` z czystą funkcją `arrange(base, pins)` (design D1); weryfikacja: testy jednostkowe — brak przypięć, przypięcie na początku/końcu/w środku, kilka przypięć, pozycja poza zakresem
- [x] 1.2 Dodać model `UserCategoryPin` (`user_category_pins`: PK `user_id, category`, `position`, `UNIQUE (user_id, position)`, kaskada przy usunięciu użytkownika) i migrację Alembic `0002`; weryfikacja: `pytest` (migracje do `head` w fixture) przechodzi, a `alembic downgrade 0001` / `upgrade head` działają na kontenerze testowym

## 2. Backend: serwis i API (spec: shopping-list)

- [x] 2.1 Dodać w serwisie listy: odczyt kolejności użytkownika, przeniesienie z przypięciem względem sąsiadów (`after`/`before`, design D2, blokada wiersza użytkownika, 400 dla sąsiada równego kategorii), odpięcie i reset; weryfikacja: testy serwisu dla scenariuszy „Przypinanie kategorii na wybranym miejscu”, „Pierwszeństwo przypiętych kategorii” i „Odpinanie kategorii”
- [x] 2.2 Uporządkować grupy w `list_out` według kolejności użytkownika i dodać pole `pinned` w grupach; `GET /api/list` i odpowiedzi mutacji listy używają kolejności zalogowanego użytkownika, czat — automatycznej; weryfikacja: istniejące testy listy i czatu przechodzą bez zmian, nowy test „Członkowie z różnymi przypięciami”
- [x] 2.3 Dodać endpointy `GET /api/list/category-order`, `PUT /api/list/category-order/{category}`, `DELETE /api/list/category-order/{category}`, `DELETE /api/list/category-order`; weryfikacja: testy API pokrywają scenariusze ze `specs/shopping-list/spec.md` (kolejność per użytkownik, trwałość, 400, 422 dla nieznanej kategorii, 409 bez gospodarstwa)

## 3. Frontend: przeciąganie nagłówków kategorii

- [x] 3.1 Dodać zależności `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` i typy (`pinned` w grupie, `CategoryMove`); weryfikacja: `npm ci` i `npx tsc -b` przechodzą
- [x] 3.2 Dodać czystą funkcję wyliczającą przeniesienie (nowa kolejność + sąsiedzi `after`/`before`) z wyniku upuszczenia; weryfikacja: testy Vitest (na początek, na koniec, w środek, upuszczenie w miejscu)
- [x] 3.3 W `ListView` zrobić z grup elementy sortowalne (`TouchSensor` z przytrzymaniem, `MouseSensor`, `KeyboardSensor`, polskie komunikaty dostępności, ruch tylko w pionie), z optymistycznym zapisem i wycofaniem przy błędzie (design D5); weryfikacja: test Vitest renderuje grupy w kolejności z API, ręczne sprawdzenie przeciągania w przeglądarce (mysz i emulacja dotyku)
- [x] 3.4 Dodać znacznik przypięcia, przycisk „Odepnij” przy przypiętej grupie i „Przywróć kolejność” (z potwierdzeniem) w pasku narzędzi; weryfikacja: testy Vitest wywołują odpowiednie `DELETE` i pokazują listę z odpowiedzi

## 4. Integracja

- [x] 4.1 Uruchomić kroki CI lokalnie: `uv run ruff check src tests evals`, `uv run ruff format --check src tests evals`, `uv run pytest`, `npm test`, `npx tsc -b`, `npx vite build`; weryfikacja: wszystkie przechodzą, a w PR zielone są checki Backend, Frontend, Docker (backend), Docker (frontend)

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`), co przeniesie wymagania do `openspec/specs/shopping-list/spec.md`.
