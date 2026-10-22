# Tasks

## 1. Backend: model i migracja

- [ ] 1.1 Dodać modele `ShoppingTrip`, `PurchasedItem`, `PurchasedNeed` (design D1) i migrację Alembic `0003` (`down_revision = "0002"`, nazwy więzów według konwencji, istniejące typy enum bez tworzenia); weryfikacja: `pytest` (migracje do `head` w fixture) przechodzi, `uv run alembic heads` pokazuje jedną głowę
- [ ] 1.2 Rozszerzyć `tests/test_migrations.py`: upgrade `0002 → head` na osobnej bazie z danymi (gospodarstwo, lista, pozycje, zapotrzebowania, przypięcia) zachowuje dane i tworzy puste tabele historii; downgrade do `0002` usuwa tylko tabele historii

## 2. Backend: zakończenie zakupów (spec: shopping-list)

- [ ] 2.1 `service.finish_shopping(session, household, user)` przenosi kupione pozycje do historii i usuwa je z listy w jednej transakcji, z blokadą listy (design D2); zakończenie bez kupionych pozycji nie tworzy wpisu; weryfikacja: testy serwisu — przeniesienie, zachowane dane (kto/kiedy/kategoria/zgłaszający/ilości/notatki), niekupione zostają, puste zakończenie, kolejne zakończenia, izolacja gospodarstw
- [ ] 2.2 `POST /api/list/finish` przekazuje zalogowanego użytkownika; weryfikacja: test API sprawdza listę po zakończeniu i wpis w historii

## 3. Czat i UI (spec: needs-chat)

- [ ] 3.1 Opis `request_finish_shopping`, pola wyniku (`bought_items_to_archive`, `archived_items`) i reguła 6 promptu mówią o przeniesieniu do historii (design D3); weryfikacja: testy narzędzi i czatu z `FakeLLMClient` sprawdzają wpis w historii po potwierdzeniu
- [ ] 3.2 Tekst potwierdzenia „Zakończ zakupy” w `frontend/src/list/ListView.tsx`; weryfikacja: `npx tsc -b`, `npm test`, `npx vite build`

## 4. Integracja

- [ ] 4.1 Kroki CI lokalnie: `uv run ruff check src tests evals`, `uv run ruff format --check src tests evals`, `uv run pytest`, frontend jak w 3.2; ewaluacja `test_finish_shopping_asks_for_confirmation` z prawdziwym modelem
