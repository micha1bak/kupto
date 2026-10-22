# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/shopping-list/spec.md`, `specs/needs-chat/spec.md`.

Stan obecny:

- `ListItem` ma `name`, `normalized_name`, `category`, `bought_at`, `bought_by_id`, `created_at`; zapotrzebowania `Need` mają `user_id`, `amount`, `unit`, `note`, `created_at`. Pozycja jest unikalna w liście po `normalized_name`.
- `kupto.lists.service.finish_shopping` wykonuje `DELETE FROM list_items WHERE bought_at IS NOT NULL` (zapotrzebowania znikają kaskadowo) i zwraca liczbę usuniętych wierszy. Woła ją `POST /api/list/finish` oraz narzędzie czatu `confirm_finish_shopping` (po `request_finish_shopping` w poprzedniej turze).
- `set_bought` nadaje wszystkim pozycjom odhaczonym jednym wywołaniem ten sam `bought_at`.
- Gospodarstwo jest usuwane (kaskadowo z listą), gdy odchodzi ostatni członek. Użytkownicy nie są usuwani, ale klucze obce do `users` w pozycjach i zapotrzebowaniach mają `ON DELETE SET NULL`.
- Produkcja przy starcie backendu wykonuje `alembic upgrade head` na bazie z prawdziwymi danymi.

Funkcje, które ten model musi umożliwić bez przebudowy:

- #37 widok historii: lista zakończeń zakupów gospodarstwa od najnowszych, w każdym kupione pozycje z ilościami i zgłaszającymi.
- #38 wyuczona kolejność kategorii i produktów per użytkownik: dla danego użytkownika kolejność jego odhaczeń (`bought_at`) w obrębie jednego zakończenia zakupów, z kategorią i znormalizowaną nazwą.
- #39 „to co zwykle”: jak często i jak regularnie gospodarstwo kupuje dany produkt (po znormalizowanej nazwie), z typową ilością.

## Goals / Non-Goals

**Goals:**

- Zachować każdą kupioną pozycję z pełną informacją kto/kiedy/co/ile/dla kogo, pogrupowaną według zakończenia zakupów.
- Przeniesienie niepodzielne i odporne na równoległe zakończenia zakupów.
- Migracja bezpieczna dla danych produkcyjnych.

**Non-Goals:**

- Endpointy i UI historii (#37), nauka kolejności (#38), podpowiedzi (#39).
- Kwoty, ceny, sklepy, wydatki.
- Odtworzenie historii sprzed wdrożenia (te pozycje zostały już usunięte).

## Decisions

### D1. Model: zakończenie zakupów → pozycje historii → zapotrzebowania historii

Trzy nowe tabele, kopia (snapshot) stanu pozycji w chwili zakończenia zakupów:

`shopping_trips` — jedno zakończenie zakupów:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | PK | |
| `household_id` | FK `households.id`, `ON DELETE CASCADE` | historia znika razem z gospodarstwem, jak lista |
| `finished_at` | `timestamptz` | |
| `finished_by_id` | FK `users.id`, `ON DELETE SET NULL`, nullable | kto nacisnął „Zakończ zakupy” |

Indeks `ix_shopping_trips_household_id_finished_at (household_id, finished_at)` — #37 (najnowsze zakończenia gospodarstwa) i #39 (zakupy gospodarstwa w czasie).

`purchased_items` — kupiona pozycja:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | PK | wstawiane w kolejności `(bought_at, list_items.id)` — rozstrzyga remisy `bought_at` |
| `trip_id` | FK `shopping_trips.id`, `ON DELETE CASCADE` | indeks |
| `name` | `varchar(100)` | nazwa wyświetlana |
| `normalized_name` | `varchar(100)` | klucz produktu dla #38/#39 |
| `category` | enum `category` (istniejący typ) | kategoria w chwili zakupu |
| `bought_at` | `timestamptz` NOT NULL | |
| `bought_by_id` | FK `users.id`, `ON DELETE SET NULL`, nullable | indeks — #38 per użytkownik |

`purchased_needs` — zapotrzebowanie, które doprowadziło do zakupu:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `id` | PK | |
| `purchased_item_id` | FK `purchased_items.id`, `ON DELETE CASCADE` | indeks |
| `user_id` | FK `users.id`, `ON DELETE SET NULL`, nullable | zgłaszający |
| `amount`, `unit`, `note` | jak w `needs` | |
| `requested_at` | `timestamptz` | `needs.created_at` |

Jak to obsługuje kolejne funkcje:

- **#37**: `shopping_trips` gospodarstwa po `finished_at DESC` + `purchased_items` + `purchased_needs`; sumy ilości liczy istniejące `aggregate_quantities`.
- **#38**: `purchased_items WHERE bought_by_id = :user` pogrupowane po `trip_id` i posortowane po `(bought_at, id)` dają sekwencje odhaczeń jednego użytkownika w jednym sklepie; `category` i `normalized_name` dają kolejność kategorii i produktów.
- **#39**: zliczenie `purchased_items` po `normalized_name` w zakończeniach gospodarstwa daje częstotliwość, odstępy `finished_at` — regularność, `purchased_needs` — typową ilość i jednostkę.

*Alternatywy:* (a) flaga „zarchiwizowana” na `list_items` zamiast osobnych tabel — koliduje z `UNIQUE (list_id, normalized_name)` (ten sam produkt kupowany co tydzień), a każde zapytanie o aktywną listę musiałoby filtrować archiwum; (b) jedna tabela z ilościami zsumowanymi i loginami w JSON — traci „kto czego potrzebował” i więzy integralności, a #38 potrzebuje `user_id`, nie loginów; (c) jedna płaska tabela pozycji bez rekordu zakończenia (grupowanie po czasie) — „w obrębie którego zakończenia zakupów” byłoby zgadywane z odstępów czasu.

Loginy nie są kopiowane: użytkownicy nie są usuwani, a ich login jest dostępny przez klucz obcy także po odejściu z gospodarstwa. Gdyby kiedyś pojawiło się usuwanie kont, `SET NULL` zachowa zakup bez autora.

### D2. Przeniesienie w jednej transakcji z blokadą listy

`finish_shopping(session, household, user)`:

1. `SELECT … FOR UPDATE` na wierszu `shopping_lists` gospodarstwa — dwa równoległe zakończenia zakupów (np. dwóch domowników) wykonują się po kolei, więc ta sama pozycja nie trafi do historii dwa razy.
2. Pobranie kupionych pozycji z zapotrzebowaniami (`FOR UPDATE` na `list_items`, żeby równoległe cofnięcie odhaczenia poczekało).
3. Brak kupionych → koniec bez zmian (wymaganie: puste zakończenie nie tworzy wpisu).
4. Wstawienie `shopping_trips`, `purchased_items`, `purchased_needs`; usunięcie pobranych pozycji po `id` (nie po predykacie `bought_at IS NOT NULL`, żeby nie usunąć pozycji odhaczonej po kroku 2, której nie ma w historii).
5. Jeden `commit` — błąd w dowolnym kroku wycofuje całość.

Funkcja nadal zwraca liczbę przeniesionych pozycji.

### D3. Teksty i narzędzia czatu

Opis `request_finish_shopping` i reguła 6 promptu mówią o przeniesieniu kupionych pozycji do historii. Pola wyniku narzędzi zmieniają nazwy na `bought_items_to_archive` i `archived_items`, żeby model nie mówił użytkownikowi o „usunięciu”. Potwierdzenie w `ListView`: „Zakończyć zakupy? Kupione pozycje zostaną przeniesione do historii.”

### D4. Migracja `0003`

Tylko `CREATE TABLE` i `CREATE INDEX` na nowych, pustych tabelach; odwołanie do istniejących typów enum `category` i `unit` bez ich tworzenia (`create_type=False`, jak w `0002`). Nie ma zmian ani blokad istniejących tabel poza krótkimi blokadami przy tworzeniu kluczy obcych do `households`/`users` (`SHARE ROW EXCLUSIVE`, natychmiastowe przy pustej tabeli źródłowej). Nazwy więzów według `NAMING_CONVENTION` z `kupto.db`. `downgrade` usuwa trzy tabele — to traci zapisaną historię, ale nie dotyka danych sprzed migracji.

## Risks / Trade-offs

- [Pozycje odhaczone jednym wywołaniem mają ten sam `bought_at`] → kolejność wewnątrz takiej paczki (np. „kupiłem mleko i chleb” w czacie) jest nieznana; `purchased_items.id` daje stabilny, ale umowny porządek. #38 powinno traktować takie remisy jako brak informacji o kolejności.
- [Historia rośnie bez końca] → kilka–kilkadziesiąt wierszy tygodniowo na gospodarstwo; retencja nie jest teraz potrzebna.
- [Kategoria w historii jest kopią] → późniejsza zmiana kategorii produktu nie zmienia historii; to zamierzone (historia opisuje stan z chwili zakupu).
- [Downgrade traci historię] → wycofanie wersji aplikacji nie wymaga downgrade’u bazy (nowe tabele nie przeszkadzają starszemu kodowi), więc downgrade jest tylko narzędziem deweloperskim.
