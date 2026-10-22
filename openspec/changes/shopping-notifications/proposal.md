# Proposal

## Why

Infrastruktura Web Push (#27) już działa na produkcji, ale nic jeszcze nie wysyła powiadomień. Domownicy dowiadują się o zakupach dopiero po otwarciu aplikacji: nie wiedzą, że ktoś właśnie idzie do sklepu (#29), kupujący nie widzi, co dopisano w trakcie (#30), a reszta nie wie, czego zabrakło (#31).

## What Changes

- **#29 „X idzie na zakupy”**: gdy status zakupów faktycznie się zaczyna (przycisk lub czat), pozostali członkowie gospodarstwa dostają „{login} idzie na zakupy” / „Dopisz, czego potrzebujesz.”. Ponowne włączenie aktywnego statusu nic nie wysyła.
- **#30 „Dopisano w trakcie”**: gdy ktoś dodaje zapotrzebowanie (REST lub czat), a inni domownicy mają aktywny status, tylko ci kupujący (bez autora) dostają powiadomienie z nazwami niekupionych produktów dopisanych przez innych w ostatnich 10 minutach (nie wcześniej niż od początku ich statusu). Stały tag per kupujący sprawia, że kolejne dopisania aktualizują jedno powiadomienie; pilność wysoka.
- **#31 „Zakupy zakończone”**: po zakończeniu zakupów z przeniesionymi pozycjami pozostali domownicy dostają „{login}: zakupy zakończone” z treścią „Nie było: …” (niekupione pozycje, które zostały na liście) albo „Wszystko kupione.”.
- Nazwy w treści: najwyżej 5, każda przycięta do 40 znaków, reszta jako „i N innych”.
- Tekst banera instalacji na iPhonie nie zapowiada już powiadomień jako „(wkrótce)”.
- Poza zakresem: ustawienia typów powiadomień (#32), zmiany schematu bazy.

## Capabilities

### New Capabilities

(brak)

### Modified Capabilities

- `notifications`: konkretne powiadomienia o zakupach (rozpoczęcie, dopisanie w trakcie, zakończenie). Capability powstaje w change `web-push` (jeszcze niezarchiwizowanym), więc wymagania są dopisywane jako ADDED.

## Impact

- **Backend**: nowy moduł `kupto.lists.notifications` (treść, adresaci, grupowanie), wywołania po commicie w `lists/router.py` (`POST /needs`, `/finish`, `/shopping`) i w narzędziach czatu (`ToolContext.notifier`, przekazywany przez `chat/router.py`). `lists/service.py` i `shopping_status.py` bez zmian.
- **API**: bez zmian w kontraktach.
- **Frontend**: tylko tekst w `InstallBanner.tsx`.
- **Dane**: bez migracji; grupowanie liczone z `needs.created_at` i `users.shopping_since`.
