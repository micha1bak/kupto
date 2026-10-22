# Tasks

## 1. Publikacja zdarzeń w backendzie

- [x] 1.1 Moduł `kupto/lists/events.py`: kanał `kupto_list`, funkcje publikujące `pg_notify` w bieżącej transakcji (`list_changed`, `order_changed`, `member_left`); test, że powiadomienie dociera do `LISTEN` dopiero po commicie, a po rollbacku wcale
- [x] 1.2 Publikacja w `lists/service.py` (wszystkie operacje zmieniające listę; `finish_shopping` tylko gdy coś przeniesiono), `lists/category_order.py` (pin/unpin/reset, tylko użytkownik z gospodarstwem) i `households/service.py` (remove_member, leave_household); testy serwisów sprawdzają dostarczone powiadomienia

## 2. Broker LISTEN i endpoint strumienia

- [x] 2.1 `ListEventBroker`: jedno połączenie asyncpg z `LISTEN`, leniwy start, subskrypcje per gospodarstwo z łączeniem sygnałów, filtrowanie po użytkowniku, zamykanie strumieni przy `left` i przy utracie połączenia, ponowne łączenie; zamknięcie w lifespan aplikacji i w fixture testów; testy brokera (izolacja gospodarstw, zakres użytkownika, `left`, utrata połączenia)
- [x] 2.2 Ustawienie `list_events_heartbeat_seconds` (domyślnie 20) i endpoint `GET /api/list/events` (401/409, `retry`, `ready`, `list_changed`, `: ping`, zwolnienie sesji bazy przed strumieniem, sprzątanie w `finally`, 503 gdy broker niedostępny); testy przez prawdziwy serwer uvicorn: zdarzenie dla swojego gospodarstwa i brak dla cudzego, heartbeat, zmiana przez czat, koniec strumienia po usunięciu z gospodarstwa, brak trzymanego połączenia z puli

## 3. Frontend

- [x] 3.1 `api/listEvents.ts`: połączenie `EventSource` (hook `useListEvents`), ponowne łączenie z wykładniczym opóźnieniem, zamykanie w tle i odświeżenie po powrocie karty; testy Vitest z atrapą `EventSource`
- [x] 3.2 `useShoppingList`: polling 30 s tylko, gdy strumień nie jest na żywo, unieważnianie listy po zdarzeniach; aktualizacja testu interwału w `ListView.test.tsx`; `npx tsc -b`, `npm test`, `npx vite build` przechodzą

## 4. Dokumentacja i weryfikacja

- [x] 4.1 README (główny, backend, frontend): opis listy na żywo (kanał, heartbeat, fallback) i ustawienia `LIST_EVENTS_HEARTBEAT_SECONDS`; limit `--timeout-graceful-shutdown` w obrazie backendu (design D9); weryfikacja przez przeczytanie
- [x] 4.2 Sprawdzenia jak w CI (ruff check/format, pytest, tsc, vitest, vite build) oraz e2e na obrazach z tej gałęzi (db + backend + nginx `web`) z dwoma klientami curl na strumieniu przez nginx — zdarzenie po zmianie listy przez drugiego członka, brak u innego gospodarstwa, heartbeat, koniec po usunięciu z gospodarstwa, wznowienie LISTEN po restarcie bazy

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`) i zsynchronizować spec `shopping-list`.
