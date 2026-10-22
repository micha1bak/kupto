# Design

## Context

Lista gospodarstwa jest odświeżana przez klientów co kilka sekund (`GET /api/list`, a w przygotowaniu strumień zmian #26), a wszystkie operacje na liście zwracają cały `ListOut`. Zakończenie zakupów (`service.finish_shopping`) zapisuje historię (`shopping_trips`). Aplikacja nie ma zadań w tle — wszystko dzieje się w obsłudze żądań. Na produkcji są prawdziwe dane, a migracje wykonują się przy starcie backendu.

## Goals / Non-Goals

**Goals:**
- Jedno źródło prawdy „kto teraz robi zakupy i od kiedy” w gospodarstwie, łatwe do odczytu dla #29–#31.
- Operacje start/stop, które mówią, czy status faktycznie się zmienił (żeby #29/#31 wysyłały powiadomienie tylko przy zmianie stanu).

**Non-Goals:**
- Model „wyprawy na zakupy” (osobna encja, uczestnicy, sklepy) i historia statusów.
- Wygaszanie statusu zadaniem w tle.
- Powiadomienia push.

## Decisions

### D1. Kolumna `users.shopping_since` zamiast osobnej tabeli

Status to jeden znacznik czasu przy użytkowniku (`TIMESTAMPTZ NULL`); NULL = nie robi zakupów. Osobna tabela (np. `shopping_sessions`) dałaby historię, ale nikt jej nie potrzebuje, a historia zakupów i tak powstaje w `shopping_trips`. Status jest per użytkownik, nie per gospodarstwo: dwie osoby mogą robić zakupy równocześnie. Migracja `0004` tylko dodaje kolumnę dopuszczającą NULL — bez przepisywania tabeli i bez zmiany istniejących wierszy; downgrade usuwa kolumnę.

### D2. Wygasanie przy odczycie

Status jest aktywny, gdy `shopping_since > teraz - 3 h` (`SHOPPING_STATUS_TTL`). Przeterminowana wartość może zostać w bazie — każdy odczyt ją ignoruje, a ponowny start ją nadpisuje. Brak zadań w tle i brak zapisów przy odczycie. Wszystkie odczyty idą przez jeden moduł (`kupto.lists.shopping_status`), więc reguła wygasania jest w jednym miejscu.

### D3. Start i stop jako warunkowe UPDATE … RETURNING

- `start(session, user) -> bool`: ustawia `shopping_since = teraz` tylko, gdy status nie jest aktywny; zwraca `True`, jeśli status właśnie się zaczął. Ponowne „idę na zakupy” w trakcie nie przesuwa `since` (czas rozpoczęcia zostaje prawdziwy, a #29 nie wyśle drugiego powiadomienia). Warunkowy UPDATE jest odporny na wyścig dwóch kliknięć.
- `stop(session, user) -> bool`: zeruje status; zwraca `True`, jeśli był aktywny.
- Odczyt dla innych modułów: `active_shoppers(session, household) -> list[Shopper]` (`user_id`, `login`, `since`, `expires_at`), najdawniej rozpoczęty pierwszy. Tak #30 wybierze adresatów „dopisano w trakcie”, a #29/#31 podłączą się pod wynik `start` / `stop` / `finish_shopping`.

Alternatywa: przedłużanie statusu przy każdym „idę na zakupy” — odrzucona, bo zacierałaby „od kiedy”, a zakupy dłuższe niż 3 h są rzadkie (po wygaśnięciu status można włączyć ponownie).

### D4. Zakończenie zakupów i odejście z gospodarstwa zdejmują status

`service.finish_shopping` zeruje status kończącego w tej samej transakcji — także gdy nie było kupionych pozycji (użytkownik jawnie skończył). Statusów innych domowników nie rusza: druga osoba może być jeszcze w innym sklepie. Odejście lub usunięcie z gospodarstwa zeruje status, żeby nie „przeszedł” do nowego gospodarstwa.

### D5. Status w odpowiedzi listy, osobne endpointy do zmiany

`ListOut.shoppers` (aktywni kupujący gospodarstwa) trafia do każdej odpowiedzi `/api/list…`. Dzięki temu istniejące odświeżanie listy (polling, a później strumień #26) pokazuje status bez nowych zapytań. Zmiana: `POST /api/list/shopping` (start) i `DELETE /api/list/shopping` (stop); oba zwracają `ListOut` jak reszta operacji na liście. Osobny endpoint odczytu nie jest potrzebny.

### D6. Czat

Narzędzia `start_shopping` i `stop_shopping` (bez argumentów; użytkownik z sesji). Wynik startu mówi, czy status już był aktywny i kto jeszcze robi zakupy. Oba należą do `LIST_CHANGING_TOOLS`, bo zmieniają `ListOut`, więc klient odświeża listę po zdarzeniu `list_changed`. Reguła promptu: „idę do sklepu / jestem w sklepie / zaczynam zakupy” → `start_shopping`; „jednak nie idę / wyszedłem ze sklepu” → `stop_shopping`; „skończyłem zakupy” → `stop_shopping` i dotychczasowy przepływ `request_finish_shopping` z potwierdzeniem. Migawka listy dla modelu zawiera `shopping_now` (loginy), więc asystent odpowie na „czy ktoś jest w sklepie?”.

### D7. UI

W pasku narzędzi listy przycisk „Idę na zakupy” (gdy zalogowany nie ma statusu) albo „Kończę” (gdy ma). „Kończę” tylko zdejmuje status; „Zakończ zakupy” (przeniesienie kupionych do historii) zostaje osobnym przyciskiem i też zdejmuje status. Nad listą wskaźnik z godziną rozpoczęcia: „Robisz zakupy od 14:05”, „ania robi zakupy od 13:50”.

## Risks / Trade-offs

- [Zapomniany status wisi do 3 h] → Akceptowalne; wygasa sam, a „Zakończ zakupy” i „Kończę” zdejmują go od razu.
- [Zakupy dłuższe niż 3 h] → Status znika; użytkownik może włączyć go ponownie.
- [Strumień zmian listy #26 powstaje równolegle] → Status jest w `ListOut`; wystarczy, że start/stop będą emitować zdarzenie zmiany listy jak inne operacje.

## Migration Plan

Migracja `0004` (`down_revision = "0003"`) dodaje `users.shopping_since TIMESTAMPTZ NULL`; wykonuje się automatycznie przy starcie backendu. Rollback: `alembic downgrade 0003` usuwa kolumnę (gubi tylko bieżące statusy).
