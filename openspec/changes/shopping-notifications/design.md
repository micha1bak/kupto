# Design

## Context

`Notifier` (change `web-push`) planuje wysyłkę w tle metodami `send_to_household` / `send_to_users`, które trzeba wołać po commicie. Status zakupów (`shopping_status`) zwraca z `start` informację, czy status faktycznie się zaczął, a `active_shoppers` podaje kupujących i początek ich statusu. Zmiany listy przechodzą przez `lists/service.py`, wywoływany z REST (`lists/router.py`) i z narzędzi czatu (`chat/tools.py`, strumień w `chat/router.py` z własną sesją bazy). Równolegle inne zmiany dotykają `lists/service.py`, dlatego logika powiadomień jest poza nim.

## Goals / Non-Goals

**Goals:**
- Jedno miejsce z treścią i wyborem adresatów dla trzech powiadomień, wołane tak samo z REST i z czatu.
- Grupowanie „Dopisano w trakcie” bez stanu w pamięci procesu i bez migracji.
- Powiadomienie nigdy nie psuje odpowiedzi na żądanie — zmiana jest już zapisana.

**Non-Goals:**
- Ustawienia typów powiadomień (#32) — `allowed_recipients` zostaje punktem zaczepienia.
- Debounce po stronie serwera (opóźniona wysyłka zbiorcza) — wymagałby stanu albo kolejki.

## Decisions

### D1. Moduł `kupto.lists.notifications` wołany przez warstwę wywołującą serwis

Funkcje `shopping_started`, `items_added`, `shopping_finished` są wywoływane w routerze REST i w narzędziach czatu zaraz po wywołaniu serwisu (który commituje). Alternatywa — wywołania wewnątrz `service.py` — wymagałaby przekazywania `Notifier` do serwisów i kolidowałaby z równoległymi zmianami w tym pliku. `items_added` i `shopping_finished` czytają bazę, więc są owinięte w ochronę „best effort”: wyjątek jest logowany, a odpowiedź idzie normalnie.

### D2. Czat: `ToolContext.notifier`

`chat/router.py` przekazuje `app.state.notifier` do strumienia odpowiedzi, a ten do `ToolContext`. Pole jest opcjonalne (domyślnie `None`) — testy narzędzi i ewaluacje działają bez powiadomień.

### D3. Grupowanie #30 przez tag i treść liczoną z bazy

Każde dodanie zapotrzebowania wysyła do każdego kupującego (poza autorem) powiadomienie z tagiem `items-added-{household}-{user}` i treścią: nazwy niekupionych pozycji, które mają zapotrzebowania innych osób niż kupujący, utworzone od `max(początek statusu, teraz − 10 min)`, najnowsze pierwsze. Urządzenie zastępuje poprzednie powiadomienie o tym samym tagu (krótki tag trafia też jako nagłówek `Topic`, więc niedoręczone starsze powiadomienie zostaje zastąpione już w usłudze push). Efekt: seria dopisań w krótkim czasie daje jedno powiadomienie z pełną, aktualną listą — bez stanu w pamięci i bez migracji.

Okno 10 min (zamiast np. 2 min) zmniejsza ryzyko, że zastąpione powiadomienie „zgubi” produkt, którego kupujący jeszcze nie zobaczył. Koszt: każde dopisanie to osobny sygnał na urządzeniu — akceptowalne, bo dopisania w trakcie zakupów są rzadkie. Pilność `high` (kupujący jest w sklepie), TTL 30 min.

### D4. Treści

- #29: tytuł „{login} idzie na zakupy”, treść „Dopisz, czego potrzebujesz.”, tag `shopping-started-{household}`.
- #30: tytuł „Dopisano w trakcie zakupów”, treść z nazwami.
- #31: tytuł „{login}: zakupy zakończone” (bez rodzaju gramatycznego), treść „Nie było: …” albo „Wszystko kupione.”, tag `shopping-finished-{household}`. Wysyłane tylko, gdy zakończenie przeniosło pozycje do historii.

Nazwy: najwyżej 5, każda do 40 znaków (z „…”), reszta „i N inny/inne/innych”. Adres po kliknięciu: `/`.

## Risks / Trade-offs

- [Dwa równoległe dopisania] → każde liczy treść po swoim commicie; później doręczone zastępuje wcześniejsze i zawiera co najmniej swoje produkty. Drobna niespójność jest akceptowalna.
- [Przygotowanie treści w żądaniu] → to jedno-dwa proste zapytania po commicie; sama wysyłka idzie w tle.
