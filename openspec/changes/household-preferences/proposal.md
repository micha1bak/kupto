# Proposal

## Why

Asystent proponuje dania, przepisy i ilości bez wiedzy o gospodarstwie: nie wie, ile osób je obiad, kto jest wegetarianinem, kto ma alergię na orzechy ani czego dzieci nie zjedzą. Domownicy muszą to powtarzać w każdej rozmowie, a pomyłka przy alergii jest kosztowna. #45 (epik #41) wprowadza preferencje gospodarstwa — wspólne dane, które czat zna i respektuje, a z których skorzysta plan obiadów (#44).

## What Changes

- Nowa encja preferencji gospodarstwa (jedna na gospodarstwo): liczba osób, diety, wykluczenia (alergie i produkty, których domownicy nie jedzą), nielubiane składniki, maksymalny czas gotowania i krótkie inne uwagi (np. budżet). Wspólne dla gospodarstwa — każdy członek je widzi i zmienia; brak zapisu = brak preferencji.
- REST API `GET`/`PUT /api/households/me/preferences` (PUT zastępuje całość).
- Czat: niepuste preferencje trafiają zwięźle do instrukcji modelu razem z regułą ich respektowania (wykluczenia nigdy, nielubiane unikać, diety, liczba osób i czas gotowania — przy propozycjach dań, przepisów i ilości). Gdy preferencji nie ma, instrukcje nie rosną. Narzędzie `update_preferences` i krótka zasada 4d: zmiana tylko na prośbę albo po potwierdzeniu propozycji.
- Frontend: sekcja „Preferencje” na stronie gospodarstwa (formularz z zapisem); odświeżenie po wymianie w czacie. Bez nowych linków w nagłówku.
- Migracja 0010 (addytywna): tabela `household_preferences`.
- Poza zakresem: plan obiadów (#44) — przygotowany jest tylko odczyt preferencji dla niego; preferencje poszczególnych osób; filtrowanie zapisanych przepisów po preferencjach; budżet jako kwota.

## Capabilities

### New Capabilities

- `household-preferences`: preferencje żywieniowe gospodarstwa i ich edycja.

### Modified Capabilities

- `needs-chat`: nowe wymagania „Preferencje gospodarstwa w propozycjach” i „Zmiana preferencji przez czat”.

## Impact

- **Backend**: `models.py` (`HouseholdPreferences`), migracja `0010_household_preferences.py`, nowy moduł `kupto/households/preferences.py`, endpointy w `households/router.py`, narzędzie w `chat/tools.py`, blok preferencji i zasada 4d w `chat/prompt.py`, odczyt w `chat/router.py`.
- **Frontend**: `household/HouseholdPreferences.tsx` na `HouseholdPage`, typy i zapytanie; odświeżenie preferencji po wymianie w czacie.
- **Koszt LLM**: jedna definicja narzędzia i jedno zdanie zasady w każdym wywołaniu; blok preferencji (kilkadziesiąt tokenów) tylko w gospodarstwach, które je ustawiły.
