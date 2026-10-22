# Tasks

## 1. Publikacja zdarzeń w backendzie

- [ ] 1.1 Moduł `kupto/lists/events.py`: kanał `kupto_list`, funkcje publikujące `pg_notify` w bieżącej transakcji (`list_changed`, `order_changed`, `member_left`); test, że powiadomienie dociera do `LISTEN` dopiero po commicie, a po rollbacku wcale
- [ ] 1.2 Publikacja w `lists/service.py` (wszystkie operacje zmieniające listę; `finish_shopping` tylko gdy coś przeniesiono), `lists/category_order.py` (pin/unpin/reset, tylko użytkownik z gospodarstwem) i `households/service.py` (remove_member, leave_household); testy serwisów sprawdzają dostarczone powiadomienia

## 2. Broker LISTEN i endpoint strumienia

- [ ] 2.1 `ListEventBroker`: jedno połączenie asyncpg z `LISTEN`, leniwy start, subskrypcje per gospodarstwo z łączeniem sygnałów, filtrowanie po użytkowniku, zamykanie strumieni przy `left` i przy utracie połączenia, ponowne łączenie; zamknięcie w lifespan aplikacji i w fixture testów; testy brokera (izolacja gospodarstw, zakres użytkownika, `left`, utrata połączenia)
- [ ] 2.2 Ustawienie `list_events_heartbeat_seconds` (domyślnie 20) i endpoint `GET /api/list/events` (401/409, `retry`, `ready`, `list_changed`, `: ping`, zwolnienie sesji bazy przed strumieniem, sprzątanie w `finally`, 503 gdy broker niedostępny); testy przez prawdziwy serwer uvicorn: zdarzenie dla swojego gospodarstwa i brak dla cudzego, heartbeat, zmiana przez czat, koniec strumienia po usunięciu z gospodarstwa, brak trzymanego połączenia z puli

## 3. Frontend

- [ ] 3.1 `api/listEvents.ts`: połączenie `EventSource` z licznikiem odwołań, ponowne łączenie z wykładniczym opóźnieniem, zamykanie w tle i odświeżenie po powrocie karty; testy Vitest z atrapą `EventSource`
- [ ] 3.2 `useShoppingList`: polling 30 s tylko, gdy strumień nie jest na żywo, unieważnianie listy po zdarzeniach; aktualizacja testu interwału w `ListView.test.tsx`; `npx tsc -b`, `npm test`, `npx vite build` przechodzą

## 4. Dokumentacja i weryfikacja

- [ ] 4.1 README/ADR: opis listy na żywo (kanał, heartbeat, fallback) i uzasadnienie braku zmian w nginx; weryfikacja przez przeczytanie
- [ ] 4.2 Sprawdzenia jak w CI (ruff check/format, pytest, tsc, vitest, vite build) oraz e2e `docker compose up --build` z dwoma klientami curl na strumieniu — zdarzenie po zmianie listy przez drugiego członka

## Workflow follow-up

- Po scaleniu PR zarchiwizować change (`/opsx:archive`) i zsynchronizować spec `shopping-list`.
