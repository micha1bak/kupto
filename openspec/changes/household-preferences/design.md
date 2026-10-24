# Design

## Context

Czat proponuje dania i ilości w zasadach 4 (ogólne potrzeby) i 4a–4c (przepisy wklejone, z linku i zapisane). Plan obiadów (#44) będzie proponował dania na wybrane dni. Ani jedno, ani drugie nie wie nic o gospodarstwie poza listą zakupów i przepisami. Ustawienia powiadomień (#32) są per użytkownik; preferencje żywieniowe dotyczą wspólnych posiłków, więc są per gospodarstwo — jak przepisy (#46).

## Goals / Non-Goals

**Goals:**
- Wspólne preferencje gospodarstwa: edycja w UI na stronie gospodarstwa, zmiana przez czat na prośbę.
- Asystent zna preferencje bez dodatkowego wywołania narzędzia i respektuje je w propozycjach.
- Jedna funkcja odczytu, z której #44 skorzysta bez przebudowy.

**Non-Goals:**
- Plan obiadów (#44), kalendarz (#47).
- Preferencje poszczególnych osób, przeliczanie przepisów na liczbę osób.
- Twarde filtrowanie przepisów lub zapotrzebowań po stronie serwera.

## Decisions

### D1. Model danych

`household_preferences`: `household_id` (PK, FK `households.id` `ON DELETE CASCADE` — jedna na gospodarstwo), `people` (`SmallInteger`, 1–20, opcjonalna), `diets`, `excluded`, `disliked` (tablice `varchar(50)`, do 20 pozycji, domyślnie puste), `max_cooking_minutes` (`SmallInteger`, 5–480, opcjonalna), `notes` (do 300 znaków, opcjonalne — np. „tanio w tygodniu”, „dzieci nie jedzą ostrego”), `updated_by_id` (FK `users.id` `SET NULL`), `updated_at`.

Brak wiersza = brak preferencji (jak domyślne ustawienia powiadomień); zapis to upsert. Pozycje list są przycinane, puste pomijane, duplikaty (bez wielkości liter) usuwane. Wolny tekst zamiast słownika, bo diety i alergie są zbyt różnorodne, a model rozumie „bez glutenu” i „celiakia” tak samo.

`excluded` łączy alergie i twarde wykluczenia („nigdy”), `disliked` — miękkie („unikaj”). Rozróżnienie alergii od np. „nie jemy wieprzowiny” nie zmienia zachowania asystenta, a jedno pole mniej to prostszy formularz i krótszy kontekst. Budżet jako kwota nie ma dziś odniesienia (aplikacja nie zna cen), więc trafia do `notes`.

Rozważone: kolumny w `households` — prościej, ale osobna tabela nie dotyka istniejących wierszy (migracja wyłącznie addytywna), a brak wiersza naturalnie znaczy „brak preferencji”.

### D2. Moduł i API

`kupto/households/preferences.py`: schemat `PreferencesIn` (walidacja i normalizacja), `load(session, household) -> Preferences` (pola oraz `updated_by`/`updated_at`; puste, gdy brak wiersza), `save(session, household, user, data)`, `for_model(prefs) -> dict` (tylko niepuste pola; pusty słownik = brak preferencji).

`GET /api/households/me/preferences` i `PUT` (zastępuje całość, odpowiada stanem po zapisie, z `updated_by` i `updated_at`). Każdy członek może zmieniać — jak przepisy.

**Pod #44**: generator planu wywoła `load` + `for_model` i przekaże wynik modelowi (ten sam blok co w czacie — `prompt.preferences_block`), a `people` posłuży za domyślną liczbę porcji.

### D3. Czat: kontekst zamiast narzędzia odczytu

Niepuste preferencje trafiają do instrukcji po danych użytkownika jako `Preferencje gospodarstwa (JSON): {...}` z jednym zdaniem reguły: składników z `excluded` nigdy nie proponuj, `disliked` unikaj, propozycje dopasuj do `diets` i `max_cooking_minutes`, a ilości do `people`; gdy użytkownik sam chce czegoś sprzecznego (np. wkleja przepis z wykluczonym składnikiem), zrób, o co prosi, i krótko o tym wspomnij. Reguła jest w bloku preferencji, a nie w stałym prompcie — gospodarstwa bez preferencji nie płacą za nią tokenami.

Rozważone: narzędzie `get_preferences` — model musiałby pamiętać, by je wywołać przed każdą propozycją (dodatkowa runda, ryzyko pominięcia przy alergii). Preferencje są krótkie (limity z D1), więc kontekst jest tańszy i pewniejszy.

### D4. Czat: zmiana preferencji

Narzędzie `update_preferences(people, diets, excluded, disliked, max_cooking_minutes, notes)` — pole `null` = bez zmian, lista zastępuje dotychczasową (aktualne wartości model ma w instrukcjach). Zasada 4d (jedno zdanie): zmieniaj tylko na prośbę użytkownika („zapamiętaj, że Ola nie je orzechów”) albo po potwierdzeniu propozycji zapisu. Zmiana jest łatwo odwracalna w UI, więc bez oczekującej akcji w bazie. Nie zmienia listy (`list_changed` = false). Wyczyszczenie liczby osób lub czasu gotowania — tylko w UI (rzadkie, a „null = bez zmian” jest prostsze dla modelu).

### D5. Frontend

Komponent `household/HouseholdPreferences.tsx` w `HouseholdPage` przed ustawieniami powiadomień: liczba osób, diety, wykluczenia, nielubiane (pola tekstowe, pozycje po przecinku), maks. czas gotowania, inne uwagi; przycisk „Zapisz preferencje” i komunikat „Zapisano”. Zapytanie `keys.householdPreferences` unieważniane po każdej wymianie w czacie (jak przepisy). Bez linku w nagłówku (#80 upraszcza nawigację).

## Risks / Trade-offs

- [Model zignoruje wykluczenie] → reguła wprost w bloku preferencji; ewaluacja z alergią; spec nie obiecuje filtrowania po stronie serwera.
- [Model zapisze preferencje z samej wzmianki] → zasada 4d i opis narzędzia; ewaluacja: wzmianka bez prośby nie zmienia preferencji.
- [Model nadpisze listę, gubiąc pozycje] → opis narzędzia: lista zastępuje dotychczasową, aktualne wartości są w instrukcjach; ewaluacja sprawdza zachowanie istniejącej pozycji; UI pozwala poprawić.
- [Więcej tokenów] → stały koszt: jedna definicja narzędzia i jedno zdanie zasady; blok preferencji tylko, gdy są ustawione.
