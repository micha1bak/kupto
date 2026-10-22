# Design

## Context

Kupto jest PWA z własnym service workerem (`frontend/src/pwa/sw.ts`, rejestracja w `register.ts`), który nie obsługuje `/api/*`. Backend (FastAPI, SQLAlchemy async) nie ma zadań w tle — wszystko dzieje się w obsłudze żądań. Status „robię zakupy” (#28) udostępnia `start`/`stop`/`active_shoppers`, pod które podłączą się powiadomienia #29–#31. Produkcja ma prawdziwe dane; sekrety trafiają z SSM do `/opt/kupto/.env` jako linie `NAZWA=wartość`, a stamtąd do zmiennych kontenera backendu.

## Goals / Non-Goals

**Goals:**
- Jedno API wysyłki, które #29–#31 wołają jedną linią po commicie, z typem powiadomienia pod ustawienia #32.
- Aplikacja działa bez kluczy VAPID (lokalnie, w CI i na produkcji przed wpisaniem kluczy).
- Wysyłka nie spowalnia ani nie psuje żądań użytkownika; martwe subskrypcje znikają same.

**Non-Goals:**
- Konkretne powiadomienia (#29–#31) i ustawienia typów (#32).
- Kolejka zadań z trwałością i ponawianiem (Celery, tabela outbox) — powiadomienia są „best effort”.
- Obsługa `pushsubscriptionchange` w SW — odnowienie załatwia synchronizacja przy otwarciu aplikacji (D8).

## Decisions

### D1. Biblioteka: `pywebpush` 2.5 z `webpush_async`

`pywebpush` (z `py-vapid` i `http-ece`) to utrzymywana implementacja szyfrowania `aes128gcm` i podpisu VAPID. Wersja 2.x ma `webpush_async` na `aiohttp`, więc wysyłka nie blokuje pętli zdarzeń i nie potrzebuje wątków. Jedna `aiohttp.ClientSession` na aplikację (tworzona przy pierwszej wysyłce, zamykana przy wyłączaniu). Limit czasu na żądanie do usługi push: 10 s (`aiohttp.ClientTimeout`). Wersje zależności w `uv.lock` wydane co najmniej 2 tygodnie przed zmianą (`aiohttp` 3.14.4, `multidict` 6.9.1, `py-vapid` 1.9.4 zamiast najnowszych).

### D2. Klucze VAPID w zmiennych środowiskowych, format base64url

`VAPID_PUBLIC_KEY` (punkt nieskompresowany P-256, base64url — wprost `applicationServerKey` w przeglądarce), `VAPID_PRIVATE_KEY` (surowe 32 bajty, base64url — jedna linia bez znaków specjalnych, więc przechodzi przez `.env` generowany z SSM; PEM z nowymi liniami by nie przeszedł), `VAPID_SUBJECT` (`mailto:` lub `https:`). Generator: `uv run python -m kupto.push.keys` wypisuje gotowe linie `NAZWA=wartość`.

Konfiguracja jest sprawdzana raz przy starcie (`VapidConfig.from_settings`): wszystkie trzy puste → powiadomienia wyłączone (log INFO); niekompletne, błędny klucz, klucz publiczny niepasujący do prywatnego albo zły `subject` → wyłączone z logiem ERROR, ale backend startuje. Alternatywa — zatrzymanie startu przy błędnej konfiguracji — odrzucona: literówka w opcjonalnym sekrecie wyłączyłaby całą aplikację.

### D3. Tabela `push_subscriptions`

`id`, `user_id` (FK `users`, `ON DELETE CASCADE`, indeks), `endpoint` (`TEXT`, unikalny), `p256dh`, `auth`, `user_agent` (≤ 300 znaków, z nagłówka `User-Agent` — do rozpoznania urządzenia przez przyszłe ustawienia), `created_at`, `updated_at`. Migracja `0005` tylko tworzy tabelę. Unikalny endpoint = jedno urządzenie należy do jednego użytkownika; zapis istniejącego endpointu przepina go na zalogowanego (`INSERT … ON CONFLICT (endpoint) DO UPDATE`). Na użytkownika trzymamy najwyżej 10 subskrypcji — przy zapisie usuwane są najdawniej odświeżone ponad limit.

### D4. Ograniczenie adresów usług push (SSRF)

Serwer wysyła żądania POST pod adres podany przez klienta, więc przyjmujemy tylko `https://` bez portu i danych logowania, z hostem w domenach usług push przeglądarek: `googleapis.com` (Chrome, Android, Opera, Samsung), `mozilla.com` (Firefox), `push.apple.com` (Safari/iOS), `notify.windows.com` (Edge). Endpoint ≤ 2048 znaków, klucze w base64url o ograniczonej długości. Nowa przeglądarka z inną usługą wymaga dopisania domeny.

### D5. API

- `GET /api/push/public-key` → `{"public_key": "..."}`; wyłączone → 404, kod `push_disabled`.
- `PUT /api/push/subscriptions` (`{endpoint, keys: {p256dh, auth}}`, kształt `PushSubscription.toJSON()`) → 204; wyłączone → 404 `push_disabled`.
- `DELETE /api/push/subscriptions` (`{endpoint}`) → 204 zawsze (idempotentnie); usuwa tylko subskrypcję zalogowanego. Endpoint w treści, nie w adresie — to adres-uprawnienie, nie powinien trafiać do logów dostępu.
- Wszystkie wymagają zalogowania (`CurrentUser`), nie wymagają gospodarstwa.

### D6. Wysyłka: `Notifier` w `app.state`, zadania `asyncio` po commicie

```python
notifier.send_to_users(user_ids, notification)
notifier.send_to_household(household_id, notification, exclude_user_ids={user.id})
```

Obie metody są synchroniczne: planują zadanie `asyncio` i od razu wracają, więc wołający (handler po `commit`, narzędzie czatu po zapisie) nie czeka na usługi push. Zadanie otwiera własną sesję bazy, wyznacza adresatów w chwili wysyłki (członkowie gospodarstwa po odejściach), przepuszcza ich przez `allowed_recipients(session, user_ids, type)` — dziś przepuszcza wszystkich, #32 doda tu filtr ustawień — i wysyła równolegle (najwyżej 10 naraz). Odpowiedź 404/410 → usunięcie subskrypcji; inne błędy, limit czasu i wyjątki sieci → log WARNING, subskrypcja zostaje. Wyjątek w zadaniu nigdy nie wychodzi poza log. Zadania są trzymane w zbiorze (żeby GC ich nie zebrał); `drain()` czeka na wszystkie (testy, wyłączanie aplikacji — `lifespan` czeka do 5 s, potem zamyka sesję HTTP).

Wysyłka wołana spoza pętli zdarzeń jest błędem programisty. Gdy powiadomienia są wyłączone, `send_*` tylko loguje (DEBUG) i nic nie planuje.

Alternatywy: `BackgroundTasks` z FastAPI — działa tylko w handlerach HTTP (nie w narzędziach czatu wołanych głębiej) i wiąże wysyłkę z cyklem odpowiedzi, w tym strumieniowanej; tabela outbox z workerem — trwałość i ponawianie nie są warte złożoności dla powiadomień „best effort”.

Transport (`PushTransport`) jest wstrzykiwany: domyślny opakowuje `webpush_async`, testy podstawiają atrapę zwracającą kody HTTP.

### D7. Treść powiadomienia

`Notification(type, title, body, url="/", tag=None, ttl=3600, urgency="normal")`; `type` to `NotificationType` (`StrEnum`) z wartościami zapowiedzianymi dla #29–#31 (`shopping_started`, `items_added`, `shopping_finished`) — wartości są stabilne, bo #32 zapisze je w ustawieniach. Do usługi push idą nagłówki `TTL`, `Urgency` (`very-low`/`low`/`normal`/`high`) i — gdy `tag` jest poprawnym tematem (≤ 32 znaki base64url) — `Topic`, dzięki któremu niedostarczone powiadomienie z tym samym tematem zostaje zastąpione. Ładunek (JSON, szyfrowany): `{type, title, body, url, tag}`.

### D8. Service worker

- `push`: parsuje JSON (niepoprawny → ogólne „Kupto”), `showNotification(title, {body, tag, renotify: !!tag, icon, badge, data: {url, type}})`. Zawsze pokazuje powiadomienie (`userVisibleOnly`).
- `notificationclick`: zamyka powiadomienie; szuka okien aplikacji (`clients.matchAll({type: "window", includeUncontrolled: true})`); jest okno → `focus()` (i `navigate(url)`, gdy jest na innej ścieżce); brak → `clients.openWindow(url)`. URL ograniczony do tej samej domeny (inaczej `/`).
- Routing `fetch` bez zmian: `/api/*` nadal z pominięciem SW.

### D9. Frontend: stan i miejsce przycisku

Logika w `pwa/push.ts` (czyste funkcje + zależności wstrzykiwane w testach), widok w `notifications/NotificationSettings.tsx`, osadzony jako karta „Powiadomienia” na stronie gospodarstwa (`/household`) — to jedyna strona ustawień, tam #32 doda przełączniki typów. Nie w `ListView`.

Stany: `loading`, `unsupported` (brak SW/PushManager/Notification), `needs-install` (iOS/iPadOS poza trybem standalone — Safari udostępnia Web Push tylko zainstalowanej aplikacji), `unavailable` (serwer zwrócił `push_disabled` albo SW nie jest zarejestrowany, np. `vite dev`), `blocked` (`Notification.permission === "denied"`), `enabled`, `disabled`.

- Przy wejściu: tylko odczyt (`permission`, `getSubscription()`, publiczny klucz) — bez pytania o zgodę. Istniejąca subskrypcja jest ponownie zapisywana na serwerze (przypisanie do zalogowanego, odtworzenie po usunięciu 410); jeśli powstała dla innego klucza VAPID (`options.applicationServerKey`), jest odnawiana.
- „Włącz”: `Notification.requestPermission()` w obsłudze kliknięcia → `pushManager.subscribe({userVisibleOnly: true, applicationServerKey})` → `PUT`. Odmowa → `blocked`.
- „Wyłącz”: `DELETE` na serwerze, potem `unsubscribe()` w przeglądarce.
- Wylogowanie: to samo co „Wyłącz” (z pominięciem błędów), zanim wylogowanie unieważni sesję — inaczej następna osoba na urządzeniu dostawałaby powiadomienia poprzedniej.

Rejestracja SW: `navigator.serviceWorker.getRegistration()`; gdy brak (dev lub jeszcze się rejestruje) — `ready` z limitem 3 s.

## Risks / Trade-offs

- [Powiadomienia giną przy restarcie backendu w trakcie wysyłki] → akceptowane („best effort”); `lifespan` czeka do 5 s na zaplanowane wysyłki.
- [Lista dozwolonych usług push może odrzucić nową przeglądarkę] → 422 z czytelnym komunikatem; dopisanie domeny to jedna linia.
- [Zmiana kluczy VAPID unieważnia subskrypcje] → klient odnawia subskrypcję przy otwarciu aplikacji (D9); stare dostaną 403/410 i zostaną usunięte (410) lub zalogowane.
- [iOS: powiadomienia tylko w zainstalowanej PWA] → stan `needs-install` z instrukcją; zgodnie z banerem instalacji.

## Migration Plan

1. Merge → migracja `0005` przy starcie backendu tworzy pustą tabelę; bez kluczy w SSM powiadomienia są wyłączone, przycisk pokazuje „niedostępne”.
2. Po merge: wygenerować klucze (`uv run python -m kupto.push.keys`), wpisać `/kupto/VAPID_PUBLIC_KEY`, `/kupto/VAPID_PRIVATE_KEY`, `/kupto/VAPID_SUBJECT` jako `SecureString`; najbliższy tick `kupto-update` odtworzy backend z kluczami.
3. Wycofanie: usunięcie parametrów VAPID wyłącza powiadomienia; `alembic downgrade 0004` usuwa tabelę (tylko subskrypcje).
