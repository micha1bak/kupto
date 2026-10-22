# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/notifications/spec.md`.

Stan obecny, który wpływa na podejście:

- `kupto.history.usual.usual_missing(session, household, now)` (#39) zwraca zwykłe produkty gospodarstwa, których brakuje na liście, z `last_bought_at` i zaległością; tylko czyta i przyjmuje `now`.
- `Notifier` (#27) wysyła do wskazanych użytkowników i sam filtruje adresatów wg ustawień typów (#32). `deliver_to_users` można wywołać i poczekać na wynik — poza obsługą żądania HTTP to właściwa ścieżka.
- Ustawienia typów (#32): nowy typ to wartość w `NotificationType` i wpis w `DEFAULT_ENABLED`, bez migracji; frontend pokazuje tylko typy, które zna.
- Produkcja to jeden serwer EC2 z Docker Compose; zadania cykliczne to timery systemd z `deploy/systemd/` (wzór: `kupto-backup.timer`), instalowane przez `install.sh` i aktualizowane/włączane przez `kupto-update.sh` (tablice `units` i `timers`). Backend działa jako jeden proces uvicorn; migracje wykonuje przy starcie.
- Wszystkie czasy w bazie są w UTC; użytkownicy są w Polsce.

## Goals / Non-Goals

**Goals:**

- Przypomnienie przychodzi samo, o rozsądnej porze, najwyżej raz dziennie na gospodarstwo.
- Te same produkty bez zmiany nie wracają w kolejnych dniach.
- Mechanizm odporny na ponowne uruchomienie, restart serwera i wdrożenie w trakcie.
- Nikt nie dostaje nowego rodzaju powiadomień bez własnej decyzji.

**Non-Goals:**

- Godzina przypomnienia wybierana przez użytkownika, strefy czasowe inne niż polska.
- Osobne przypomnienia per użytkownik (treść jest wspólna dla gospodarstwa, jak podpowiedzi przy liście).
- Akcje w powiadomieniu (dopisanie bez otwierania aplikacji).
- Usługi harmonogramu AWS (EventBridge Scheduler) i kolejki zadań.

## Decisions

### D1. Uruchamianie: timer systemd → komenda w kontenerze backendu

`kupto-reminders.timer` codziennie o **17:00 Europe/Warsaw** (`OnCalendar=*-*-* 17:00:00 Europe/Warsaw`, `Persistent=true`) uruchamia `kupto-reminders.service`, a ta skrypt `deploy/kupto-reminders.sh`: `docker compose exec -T backend python -m kupto.history.reminders` pod wspólną blokadą `/run/kupto.lock` (jak zrzut bazy — wdrożenie nie odtworzy kontenera w trakcie wysyłki). Komenda tworzy własny `Notifier` z tych samych ustawień co aplikacja, wysyła, czeka na wynik i kończy się.

Dlaczego tak:

- Ten sam wzorzec co `kupto-backup` — znane miejsce w `deploy/`, wynik w `journalctl -u kupto-reminders`, ręczne uruchomienie `systemctl start kupto-reminders`, `systemctl list-timers` pokazuje następne uruchomienie.
- Kod w obrazie backendu (te same zależności, zmienne środowiskowe i klucze VAPID), bez nowego kontenera ani usługi AWS. EventBridge Scheduler wymagałby wywołania serwera z zewnątrz (nowy endpoint z uwierzytelnieniem albo SSM Run Command z rolą) — za dużo jak na jeden serwer.
- Pętla w aplikacji (zadanie `asyncio` w `lifespan`) też by zadziałała, ale wiązałaby harmonogram z cyklem życia procesu WWW (restart przy każdym wdrożeniu, gubione uruchomienia, trudniejsze testy i ręczne wywołanie), a przy kilku workerach wysyłałaby wielokrotnie.
- Strefa czasowa w `OnCalendar` obsługuje systemd ≥ 241 (Amazon Linux 2023 ma 252); 17:00 to pora, gdy zwykle planuje się zakupy po pracy.

Jedno uruchomienie dziennie przechodzi po wszystkich gospodarstwach (skala domowa — kilka gospodarstw, każde to kilka zapytań).

### D2. Limity w kodzie, nie w harmonogramie

Harmonogram może zawieść w obie strony (`Persistent=true` nadrabia pominięte uruchomienie po starcie serwera, ktoś uruchomi usługę ręcznie dwa razy), więc limity pilnuje komenda:

1. **Pora**: wysyłka tylko między 9:00 a 21:00 czasu polskiego (`SEND_FROM`, `SEND_UNTIL`); poza tym oknem komenda kończy się bez zmian (nadrobione po nocnym starcie serwera przypomnienie nie budzi nikogo).
2. **Raz dziennie na gospodarstwo**: gdy gospodarstwo dostało już przypomnienie w tej samej dobie czasu polskiego (najnowszy `reminded_at` w `usual_reminders`), jest pomijane.
3. **Tylko coś nowego**: produkt z `usual_missing` jest *nowy*, gdy gospodarstwo nie dostało o nim przypomnienia albo kupiło go po ostatnim przypomnieniu (`reminded_at < last_bought_at`). Przypomnienie idzie tylko, gdy jest co najmniej jeden nowy produkt. Dzięki temu „mleko” przypomniane w poniedziałek nie wraca we wtorek i środę, ale po kolejnym zakupie mleka i upływie typowego odstępu znów może trafić do przypomnienia.
4. Treść zawiera **wszystkie** brakujące zwykłe produkty (nowe pierwsze, potem wg zaległości) — powiadomienie ma odpowiadać temu, co użytkownik zobaczy w podpowiedziach po kliknięciu. Po wysyłce wszystkie wymienione produkty dostają `reminded_at = now`.

Decyzja i zapis dla gospodarstwa odbywają się w jednej transakcji z blokadą wiersza gospodarstwa (`SELECT … FOR UPDATE`), więc dwa równoległe uruchomienia nie wyślą dwóch przypomnień. Zapis następuje **przed** wysyłką (jak pozostałe powiadomienia — wysyłka po commicie): błąd usługi push nie powoduje ponawiania i zalewu przypomnień; w najgorszym razie jedno przypomnienie przepada.

### D3. Model danych: `usual_reminders`

| Kolumna | Typ | Uwagi |
|---|---|---|
| `household_id` | FK `households.id`, `ON DELETE CASCADE` | część PK |
| `normalized_name` | `varchar(100)` | część PK — jak w historii zakupów |
| `reminded_at` | `timestamptz NOT NULL` | ostatnie przypomnienie o produkcie |

Zapis to `INSERT … ON CONFLICT DO UPDATE`. Najnowszy `reminded_at` gospodarstwa to chwila ostatniego przypomnienia (limit dzienny) — bez osobnej kolumny w `households`. Wiersze starsze niż okno historii `usual_missing` (365 dni) są usuwane przy kolejnym przypomnieniu gospodarstwa — i tak nie mogą już wpłynąć na wynik. Liczba wierszy jest ograniczona liczbą różnych produktów kupowanych przez gospodarstwo.

Alternatywy odrzucone: sama data ostatniego przypomnienia w `households` (nie odróżnia „te same produkty” od „nowy produkt”), skrót zestawu produktów (zmiana kolejności lub zniknięcie jednego produktu wyglądałyby jak nowy zestaw).

### D4. Adresaci i typ domyślnie wyłączony

`NotificationType.USUAL_REMINDER = "usual_reminder"` z `DEFAULT_ENABLED = False`: przypomnienie generuje aplikacja (nie domownik), codziennie — to inny charakter niż dotychczasowe powiadomienia, więc włącza się je świadomie przełącznikiem „Zwykłe produkty” na karcie „Powiadomienia”.

Adresaci: członkowie gospodarstwa, którzy chcą dostać ten typ (`preferences.recipients_wanting`) i mają co najmniej jedną subskrypcję. Gdy takich nie ma — albo powiadomienia są wyłączone na serwerze (brak kluczy VAPID) — gospodarstwo jest pomijane **bez zapisu**, więc osoba, która włączy przypomnienia później, dostanie też produkty, które już wcześniej brakowały.

### D5. Treść

- Tytuł: „Zwykle o tej porze kupujecie”.
- Treść: „{nazwy} — dopisać do listy?”, nazwy przez `format_names` z `kupto.lists.notifications` (najwyżej 5, „i N innych”).
- `url="/"` (lista z podpowiedziami #39, z których dodaje się jednym kliknięciem), tag `usual-reminder-{household_id}` (nowe przypomnienie zastępuje wczorajsze), `ttl` 4 godziny (nie doręczamy przypomnienia w środku nocy), pilność `normal`.

### D6. Strefa czasowa

`zoneinfo.ZoneInfo("Europe/Warsaw")` z zależnością `tzdata` — działa także, gdy obraz systemu nie ma bazy stref czasowych (obraz `python:*-slim` nie gwarantuje jej w kolejnych wersjach).

## Risks / Trade-offs

- [Timer nie działa, gdy serwer jest wyłączony o 17:00] → `Persistent=true` nadrabia po starcie, a okno 9–21 chroni przed wysyłką w nocy.
- [Kontener backendu nie działa w chwili uruchomienia (np. awaria)] → `docker compose exec` kończy się błędem widocznym w `journalctl -u kupto-reminders`; kolejna próba następnego dnia. Wdrożenie w trakcie nie przeszkadza dzięki wspólnej blokadzie.
- [Przypomnienie zapisane, a wysyłka się nie udała] → przypomnienie przepada (świadomie — lepsze niż powtarzanie); błąd w logach.
- [Jedno przypomnienie dla gospodarstwa wg jednej godziny] → wystarczające dla rodziny w jednym kraju; godzina to stała w timerze.
- [Produkt usunięty z listy bez zakupu] → nie jest „nowy” (nie został kupiony od przypomnienia), więc nie wraca w przypomnieniu, ale nadal jest w podpowiedziach przy liście.

## Migration Plan

Migracja `0008` (`down_revision = "0007"`) tylko tworzy pustą tabelę — wdrożenie bez przestoju. Kolejność po merge: backend z migracją wdraża się sam (`kupto-update`); timer włącza się sam przy drugim ticku `kupto-update` (pierwszy wykonuje jeszcze starą wersję skryptu). Do 17:00 i tak nikt nie ma włączonego typu, więc kolejność nie ma znaczenia. Downgrade usuwa tabelę: gospodarstwa mogą dostać ponownie przypomnienie o produktach, o których już było.

Wycofanie bez downgrade'u: `systemctl disable --now kupto-reminders.timer` na serwerze (wraca przy kolejnym ticku `kupto-update`, dopóki timer jest w tablicy `timers`) albo usunięcie timera z `timers` w repo.
