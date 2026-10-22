# Proposal

## Why

„Zakończ zakupy” (#36) zapisuje kupione pozycje w historii gospodarstwa, ale nikt nie może jej obejrzeć. Domownicy chcą sprawdzić, co i kiedy kupiono, kto to zgłaszał i kupował, oraz szybko odpowiedzieć na pytanie „kiedy ostatnio kupowaliśmy kawę i kto?” (#37).

## What Changes

- Nowe API tylko do odczytu, ograniczone do gospodarstwa zalogowanego:
  - `GET /api/history` — zakończenia zakupów od najnowszych, stronicowane kursorem (`before` = id ostatniego zakończenia z poprzedniej strony, `limit`); w każdym: czas, kto zakończył, pozycje pogrupowane po kategorii (w kolejności kategorii użytkownika) z czasem i autorem zakupu, zgłaszającymi i sumami ilości.
  - `GET /api/history/products?q=…` — wyszukiwanie produktu w historii bez względu na wielkość liter i polskie znaki; dla każdego pasującego produktu: kiedy i kto ostatnio go kupił, ile razy był kupowany i ilość z ostatniego zakupu.
- Nowy widok „Historia” (`/history`) dostępny z nagłówka aplikacji: zakończenia jako sekcje z datą i osobą, pozycje pogrupowane po kategorii, pole wyszukiwania produktu i przycisk „Pokaż więcej”.
- Bez kwot i wydatków (decyzja właściciela) i bez zmian schematu bazy (bez migracji).
- Poza zakresem: usuwanie i edycja historii, statystyki, podpowiedzi z historii w czacie.

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `shopping-list`: nowe wymagania — przeglądanie historii zakupów i wyszukiwanie produktu w historii.

## Impact

- **Backend**: moduł `kupto.history` (serwis odczytu i router `/api/history`), jedna linia rejestracji routera w `main.py`. Bez migracji.
- **API**: dwa nowe endpointy GET; istniejące bez zmian.
- **Frontend**: strona `HistoryPage` (`/history`), link „Historia” w nagłówku `MainPage`, trasa w `App.tsx`, typy i funkcje formatowania dat.
- **Wydajność**: wyszukiwanie to skan pozycji historii gospodarstwa (`translate(lower(...)) LIKE`); przy dużej historii można dodać indeks trigramowy (propozycja na później, wymaga migracji).
