# Design

## Context

Historia zakupów gospodarstwa to `shopping_trips` (`household_id`, `finished_at`), `purchased_items` (`name`, `normalized_name`, `category`, `bought_at`) i `purchased_needs` (`amount`, `unit`, `user_id`). Lista bieżąca scala pozycje po `normalized_name`. Odczyt historii żyje w `kupto.history` (D1 z `purchase-history-view`). Równolegle powstaje migracja `0006` (kolejność produktów), więc ta zmiana nie może dodawać migracji. Kolejne zadanie (#40, przypomnienia push) użyje tego samego wykrywania.

## Goals / Non-Goals

**Goals:**
- Prosta, przewidywalna i opisana heurystyka „co zwykle kupujemy, a czego teraz brakuje”.
- Jedna funkcja serwisu używana przez API, czat i później powiadomienia.
- Dyskretna podpowiedź w UI, której łatwo użyć i łatwo się pozbyć.

**Non-Goals:**
- Uczenie maszynowe, sezonowość, dni tygodnia, prognozy ilości.
- Zapamiętywanie odrzuconych podpowiedzi na serwerze (wymagałoby migracji).
- Powiadomienia (#40).

## Decisions

### D1. Heurystyka „to co zwykle”

Dla gospodarstwa i chwili `now`:

1. Bierzemy pozycje historii z zakończeń zakupów z ostatnich **365 dni** (`finished_at ≥ now − 365 dni`) i grupujemy je po `normalized_name`.
2. **Data zakupu** produktu to `finished_at` zakończenia, w którym był (jedno zakończenie = jeden zakup, nawet przy kilku zgłaszających).
3. Produkt jest **regularny**, gdy był kupiony w co najmniej **3** różnych zakończeniach (`MIN_PURCHASES = 3`). Mniej historii = brak podpowiedzi (zimny start).
4. **Typowy odstęp** = mediana odstępów między kolejnymi zakupami produktu, nie mniej niż **1 dzień** (dwa zakończenia jednego dnia nie robią z produktu „codziennego”).
5. **Zaległość** = (`now` − ostatni zakup) / typowy odstęp. Podpowiadamy, gdy **0,8 ≤ zaległość ≤ 3**: od 0,8 — bo lepiej dopisać chwilę przed końcem zapasu; do 3 — dłuższa przerwa znaczy raczej, że gospodarstwo przestało to kupować.
6. Pomijamy produkty, które **są teraz na liście** (dowolna pozycja z tym samym `normalized_name`, także odhaczona).
7. **Nazwa i kategoria** — z ostatniego zakupu.
8. **Typowa ilość**: dla każdego zakupu sumujemy ilości zapotrzebowań w każdej jednostce (`aggregate_quantities`); jednostka = ta, w której ilość podano w największej liczbie zakupów (remis — jednostka z ostatniego zakupu); ilość = mediana sum w tej jednostce. Brak ilości w historii = brak typowej ilości.
9. Kolejność: największa zaległość pierwsza, potem częściej kupowane, potem nazwa.

Mediana zamiast średniej, żeby jeden wyjazd czy jednorazowe podwójne zakupy nie psuły rytmu. Wszystkie progi to stałe w `kupto/history/usual.py`.

### D2. Funkcja serwisu dla API, czatu i #40

`kupto.history.usual.usual_missing(session, household, now=None) -> list[Suggestion]`, gdzie `Suggestion` (frozen dataclass): `name`, `normalized_name`, `category`, `amount: Decimal | None`, `unit: Unit | None`, `times_bought`, `typical_interval: timedelta`, `last_bought_at`, `since_last: timedelta`, `overdue: float`. Funkcja tylko czyta (jedno zapytanie o historię z oknem 365 dni + jedno o nazwy na liście) i filtruje po `household.id`. `now` jest parametrem, żeby testy i przypomnienia mogły liczyć na konkretną chwilę.

### D3. API: `GET /api/history/usual`

W routerze `kupto.history` (moduł historii, bez dotykania `lists/router.py`, nad którym trwają inne prace). Wymaga gospodarstwa (409 bez niego, 401 bez sesji). Zwraca najwyżej 20 podpowiedzi: `name`, `category`, `amount`, `unit`, `times_bought`, `typical_interval_days`, `last_bought_at`, `overdue`.

### D4. Czat: narzędzie `get_usual_missing` i zasada w prompcie

Narzędzie tylko do odczytu (nie w `LIST_CHANGING_TOOLS`) zwraca do 10 podpowiedzi w zwięzłej postaci (`name`, `category`, `typical_amount`, `unit`, `bought_times`, `every_days`, `days_since_last`). Nowa zasada w prompcie: na pytania typu „czego nam zwykle brakuje?”, „co zwykle kupujemy?” wywołaj `get_usual_missing`, zaproponuj produkty z typową ilością i zapytaj o potwierdzenie — dodawaj dopiero po potwierdzeniu, tak jak przy ogólnej potrzebie (zasada 4). Pusty wynik: powiedz, że nic zwykłego teraz nie brakuje albo historia jest jeszcze za krótka. Zasadę dopisujemy do zasady 4, żeby nie przenumerowywać pozostałych.

### D5. UI: `UsualSuggestions` nad listą

Osobny komponent w `frontend/src/list/UsualSuggestions.tsx`, wpięty w `ListView.tsx` jedną linią (prop: bieżąca lista). Pokazuje „Zwykle kupujecie:” i do 6 produktów jako przyciski „+ mleko · 2 l”; kliknięcie wysyła zwykłe `POST /api/list/needs` z nazwą, kategorią i typową ilością i podmienia listę w cache. Podpowiedzi filtrujemy też po stronie klienta względem bieżącej listy, żeby dodany produkt znikał od razu. „Ukryj na dziś” zapisuje lokalną datę w `localStorage` (`kupto.usualHiddenOn`); następnego dnia podpowiedź wraca. Błędy `localStorage` są ignorowane (podpowiedź po prostu się pokazuje). Brak podpowiedzi lub błąd zapytania = komponent nic nie renderuje.

## Risks / Trade-offs

- [Produkt pod różnymi nazwami („mleko”, „mleko 2%”)] → liczone osobno; scalanie nazw poza zakresem.
- [Rzadkie zakończenia zakupów — wszystko kupowane razem] → typowy odstęp to rytm zakończeń; to zgodne z tym, jak gospodarstwo robi zakupy.
- [Ukrycie tylko na jednym urządzeniu] → wystarczające dla dyskretnej podpowiedzi; serwerowe wykluczenia wymagałyby migracji.
- [Pełne przeliczenie przy każdym zapytaniu] → przy historii jednego gospodarstwa z roku to setki wierszy; w razie potrzeby można dodać cache.
