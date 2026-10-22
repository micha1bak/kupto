# Proposal

## Why

Gospodarstwo kupuje wiele produktów regularnie (mleko co kilka dni, papier toaletowy co dwa tygodnie), a i tak ktoś musi o nich pamiętać i wpisać je na listę. Historia zakupów (#36, #37) już wie, co i jak często kupujemy — może podpowiedzieć „to co zwykle”, czego teraz brakuje na liście (#39). To samo wykrywanie posłuży później przypomnieniom push (#40).

## What Changes

- Wykrywanie „zwykłych” produktów, których nie ma teraz na liście: prosta, przewidywalna heurystyka na historii gospodarstwa (co najmniej 3 zakupy w ostatnim roku, mediana odstępów między zakończeniami zakupów z produktem jako typowy odstęp, „zaległość” = czas od ostatniego zakupu / typowy odstęp w przedziale 0,8–3), typowa ilość z dawnych zapotrzebowań. Bez ML; mało historii = brak podpowiedzi.
- Funkcja serwisu `usual_missing(session, household, now)` zwracająca listę podpowiedzi (nazwa, kategoria, typowa ilość, liczba zakupów, typowy odstęp, ostatni zakup, zaległość) — do ponownego użycia w #40.
- API tylko do odczytu: `GET /api/history/usual` dla gospodarstwa zalogowanego.
- Czat: narzędzie tylko do odczytu `get_usual_missing` i zasada w prompcie — na pytania „czego nam zwykle brakuje?”, „co zwykle kupujemy?” asystent proponuje produkty z typową ilością i dodaje je dopiero po potwierdzeniu (jak przy ogólnych potrzebach).
- UI: dyskretna podpowiedź nad listą „Zwykle kupujecie: …” z dodaniem produktu jednym kliknięciem (zwykłe zapotrzebowanie z typową ilością) i ukryciem podpowiedzi do końca dnia (pamiętane w przeglądarce).
- Bez zmian schematu bazy (bez migracji).
- Poza zakresem: powiadomienia push (#40), uczenie maszynowe, sezonowość, ręczne wykluczanie produktów z podpowiedzi.

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `shopping-list`: nowe wymaganie — podpowiedzi produktów kupowanych zwykle, których brakuje na liście.
- `needs-chat`: nowe wymaganie — asystent podpowiada zwykłe produkty i dodaje je po potwierdzeniu.

## Impact

- **Backend**: `kupto/history/usual.py` (heurystyka), schemat i endpoint w `kupto/history/`, narzędzie w `chat/tools.py`, zasada w `chat/prompt.py`. Bez migracji.
- **API**: jeden nowy endpoint GET; istniejące bez zmian.
- **Frontend**: komponent `list/UsualSuggestions.tsx` wpięty jedną linią w `ListView.tsx`, zapytanie w `api/queries.ts`, typ w `api/types.ts`.
- **Wydajność**: jedno zapytanie o pozycje historii gospodarstwa z ostatniego roku i liczenie w Pythonie — przy domowej skali (setki pozycji) pomijalne.
