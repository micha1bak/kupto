# Proposal

## Why

Od #29–#31 domownicy dostają trzy rodzaje powiadomień o zakupach, ale mogą je tylko włączyć albo wyłączyć w całości na urządzeniu. Kto chce wiedzieć, czego zabrakło w sklepie, a nie potrzebuje sygnału przy każdym wyjściu domownika na zakupy, musi dziś wybierać między zalewem powiadomień a ciszą. Ustawienia typów powiadomień (#32) pozwalają każdemu wybrać, o czym chce być powiadamiany.

## What Changes

- Każdy użytkownik może włączyć lub wyłączyć osobno każdy typ powiadomień: „Ktoś idzie na zakupy” (#29), „Dopisano w trakcie zakupów” (#30), „Zakupy zakończone” (#31).
- Ustawienia są **per użytkownik** (obowiązują na wszystkich jego urządzeniach) i niezależne od włączenia powiadomień na urządzeniu; domyślnie wszystkie typy są włączone, więc nic się nie zmienia dla obecnych użytkowników.
- Wysyłka pomija użytkowników, którzy wyłączyli dany typ — dotyczy powiadomień do gospodarstwa i do wskazanych użytkowników.
- Nowe endpointy `GET /api/push/preferences` i `PUT /api/push/preferences/{type}`.
- Na karcie „Powiadomienia” (strona gospodarstwa) pola wyboru typów pod przyciskiem włączania powiadomień na urządzeniu.
- Nowa tabela ustawień (migracja Alembic `0007`, wyłącznie addytywna). Typ powiadomienia zapisany jako tekst, a wartość domyślna wynika z kodu, więc kolejne typy (np. przypomnienia z #40, także domyślnie wyłączone) nie wymagają migracji.
- Poza zakresem: ustawienia per urządzenie, godziny ciszy, sam typ przypomnień (#40).

## Capabilities

### New Capabilities

(brak)

### Modified Capabilities

- `notifications`: ustawienia typów powiadomień per użytkownik i ich respektowanie przy wysyłce. Capability powstaje w change `web-push` (jeszcze niezarchiwizowanym), więc wymagania są dopisywane jako ADDED.

## Impact

- **Backend**: model `NotificationPreference` i tabela `notification_preferences` (migracja `0007`), moduł `kupto.push.preferences` (wartości domyślne, odczyt, zapis, filtr adresatów), `allowed_recipients` w `kupto.push.notifier` korzysta z filtra, nowe endpointy w `push/router.py`.
- **API**: zmiana zgodna wstecz — tylko nowe endpointy.
- **Frontend**: `NotificationSettings` pokazuje przełączniki typów (TanStack Query, aktualizacja optymistyczna).
- **Dane**: brak wiersza = wartość domyślna typu; usunięcie użytkownika usuwa jego ustawienia (`ON DELETE CASCADE`).
