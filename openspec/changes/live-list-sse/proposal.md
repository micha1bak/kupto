# Proposal

## Why

Lista odświeża się dziś pollingiem co 5 s: zmiany innych domowników docierają z opóźnieniem, a każdy otwarty klient co 5 s pobiera całą listę, nawet gdy nic się nie zmieniło (także w tle, na telefonie w sklepie). ADR 0001 od początku zakłada listę na żywo przez SSE i Postgres `LISTEN/NOTIFY` (#26) — czat już strumieniuje, a infrastruktura (Caddy, nginx bez buforowania) jest gotowa.

## What Changes

- Nowy endpoint `GET /api/list/events` — strumień SSE z sygnałem „lista gospodarstwa się zmieniła” (bez treści listy), autoryzowany jak reszta `/api/list` (ciasteczko sesji, wymagane gospodarstwo). Strumień kończy się, gdy użytkownik przestaje być członkiem gospodarstwa.
- Każda zmiana listy (ręcznie przez REST i przez czat) oraz zmiana kolejności kategorii użytkownika publikuje zdarzenie przez Postgres `NOTIFY` w tej samej transakcji (dostarczane dopiero po commicie). Backend nasłuchuje `LISTEN` jednym połączeniem na proces i rozprowadza sygnały do subskrybentów; działa przy wielu instancjach backendu.
- Heartbeat co 20 s, żeby pośrednicy (Caddy, nginx z `proxy_read_timeout 300s`) nie zamykali bezczynnych połączeń; sprzątanie subskrypcji po rozłączeniu klienta.
- Frontend: `EventSource` z automatycznym ponownym łączeniem; po zdarzeniu ponowne pobranie listy zwykłym `GET /api/list`. Polling zostaje tylko jako fallback (co 30 s), gdy strumień nie działa; po powrocie karty/aplikacji na pierwszy plan lista jest odświeżana od razu, a karta w tle zamyka strumień.
- Bez migracji bazy i bez nowych zależności.

## Capabilities

### New Capabilities

<!-- Brak — to sposób dostarczania zmian wspólnej listy. -->

### Modified Capabilities

- `shopping-list`: wymaganie „Widoczność zmian innych członków” — zmiany docierają na żywo (w ciągu kilku sekund), najpóźniej po 30 s, gdy połączenie na żywo jest niedostępne, i od razu po powrocie do aplikacji; nowe wymagania dotyczące strumienia zmian listy (autoryzacja, izolacja gospodarstw, podtrzymanie i ponowne łączenie).

## Impact

- **Backend**: nowy moduł `kupto/lists/events.py` (publikacja `pg_notify` + broker `LISTEN` z ponownym łączeniem); publikacja w `lists/service.py`, `lists/category_order.py`, `lists/shopping_status.py` (status „Idę na zakupy” jest częścią odpowiedzi listy) i `households/service.py` (zakończenie strumienia po opuszczeniu gospodarstwa); endpoint w `lists/router.py`; zamknięcie brokera w lifespan aplikacji; ustawienie `LIST_EVENTS_HEARTBEAT_SECONDS`. Narzędzia czatu bez zmian — publikują przez serwis.
- **Frontend**: `api/listEvents.ts` (połączenie `EventSource`, ponowne łączenie, widoczność karty); `useShoppingList` przełącza polling na fallback 30 s.
- **Infrastruktura**: `frontend/nginx.conf` i Caddy już przepuszczają SSE bez buforowania dla `/api/`, a heartbeat mieści się w ich limitach czasu. Każdy otwarty klient trzyma jedno długie połączenie HTTP (ale nie połączenie z bazą).
- **API**: zmiana zgodna wstecz — nowy endpoint, istniejące bez zmian.
