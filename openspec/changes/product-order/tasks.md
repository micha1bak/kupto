# Tasks

## 1. Backend: model i wyliczanie kolejności

- [x] 1.1 Dodać do `kupto.lists.ordering` czystą funkcję `arrange_anchored(base, pins)` z kotwicami (początek, za elementem, koniec) i rangą (design D2); weryfikacja: testy jednostkowe — brak przypięć, początek/koniec/za elementem, kilka przypięć z tą samą kotwicą, zmieniona baza (#38), przypięcia i kotwice spoza bazy
- [x] 1.2 Dodać model `UserProductPin` (`user_product_pins`) i migrację Alembic `0006` (`down_revision = "0005"`); weryfikacja: test w `tests/test_migrations.py` — upgrade 0005→0006 nie zmienia istniejących danych, tabela przyjmuje przypięcia, `UNIQUE (user_id, category, position)` działa, downgrade do 0005 i ponowny upgrade; `uv run alembic heads` pokazuje jedną głowę

## 2. Backend: serwis i API (spec: shopping-list)

- [x] 2.1 Dodać moduł `kupto.lists.product_order`: kolejność bazowa `product_base_order` (alfabetycznie — punkt podpięcia #38), odczyt przypięć użytkownika (`ProductOrder`), przypięcie względem sąsiadów (design D3, blokada użytkownika, 400/404/409) i odpięcie, z `events.order_changed`; weryfikacja: testy serwisu dla scenariuszy „Przypinanie produktu…”, „Pierwszeństwo przypiętych produktów”, „Odpinanie produktu” oraz sprawdzenie, że kolejność po przypięciu jest dokładnie tą z upuszczenia
- [x] 2.2 Uporządkować pozycje w grupach `list_out` według `ProductOrder` i dodać pole `pinned` w `ItemOut`; `GET /api/list` i odpowiedzi mutacji używają przypięć zalogowanego użytkownika, czat — kolejności bazowej; weryfikacja: istniejące testy listy i czatu przechodzą, nowy test „Członkowie z różnie przypiętymi produktami”
- [x] 2.3 Dodać endpointy `PUT /api/list/items/{item_id}/order` i `DELETE /api/list/items/{item_id}/order`; weryfikacja: testy API (kolejność per użytkownik, przypięcie przy kolejnym dodaniu produktu po zakończeniu zakupów, 400 dla sąsiada z innej kategorii i samego siebie, 404 dla cudzej pozycji, sygnał listy na żywo)

## 3. Frontend: przeciąganie produktów

- [x] 3.1 Dodać typy (`pinned` w pozycji, `ItemMove`) i uogólnić wyliczanie upuszczenia na dowolne identyfikatory; dodać przestawienie pozycji w grupie (aktualizacja optymistyczna); weryfikacja: testy Vitest funkcji czystych
- [x] 3.2 W `GroupSection` dodać zagnieżdżony `DndContext`/`SortableContext` dla pozycji z uchwytem w wierszu (przytrzymanie na dotyku, mysz, klawiatura, polskie komunikaty), optymistyczny zapis z wycofaniem przy błędzie; weryfikacja: test Vitest — przeniesienie pozycji z klawiatury wysyła `PUT` z sąsiadami i przestawia wiersze, błąd przywraca kolejność, przeciąganie nagłówków kategorii nadal przechodzi istniejące testy
- [x] 3.3 Dodać znacznik 📌 i „Odepnij” przy przypiętym produkcie; weryfikacja: test Vitest wywołuje `DELETE /api/list/items/{id}/order` i pokazuje listę z odpowiedzi

## 4. Integracja

- [x] 4.1 Uruchomić kroki CI lokalnie: `uv sync --locked`, `uv run ruff check src tests evals`, `uv run ruff format --check src tests evals`, `uv run pytest`, `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`, oraz `uv run alembic heads`; weryfikacja: wszystkie przechodzą, jedna głowa migracji

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`), co przeniesie wymagania do `openspec/specs/shopping-list/spec.md`.
- Ręcznie sprawdzić przeciąganie produktu na telefonie (Android, iPhone) na produkcji.
