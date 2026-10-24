# Proposal

## Why

Dziś każdy domownik rozmawia z asystentem we własnym, prywatnym wątku — nie widzi, co inni już zgłosili, a asystent nie zna rozmów pozostałych. #78 zmienia czat asystenta w czat grupowy gospodarstwa: gospodarstwo „Dom” = czat „Dom”, w którym piszą wszyscy domownicy, a asystent odpowiada w kontekście całej rozmowy. Żeby w takim czacie było wiadomo, kto co napisał, konto potrzebuje imienia — login (który #77 zastąpi adresem e-mail) się do tego nie nadaje. Kolejność prac ustalona z użytkownikiem: #79 (zrobione), #78, potem #77 — dlatego wymagane imię dodajemy teraz, a logowania nie ruszamy.

## What Changes

- **Imię użytkownika**: nowe pole `name` (1–40 znaków po przycięciu spacji), wymagane przy rejestracji, edytowalne na stronie profilu (`PATCH /api/users/me`), zwracane w profilu. Istniejące konta bez imienia po zalogowaniu widzą blokujący ekran „Jak masz na imię?” — reszta aplikacji jest niedostępna, dopóki go nie uzupełnią. Login bez zmian (zmieni go #77).
- **Jeden wątek gospodarstwa**: `GET /api/chat/messages` zwraca wiadomości wszystkich domowników i odpowiedzi asystenta (ostatnie 200), każda z autorem (`author: {id, name}` dla wiadomości członka, `null` dla asystenta), flagą `mine` i czasem utworzenia.
- **Dotychczasowe prywatne historie** trafiają do archiwum: zostają w bazie, oznaczone `private = true`, nie są widoczne w wątku gospodarstwa ani w kontekście modelu (decyzja D2). Autor może je przejrzeć tylko do odczytu: `GET /api/chat/archive` i link „Moje dawne rozmowy” w opcjach czatu (ukryty przy pustym archiwum). Cofnięcie migracji przywraca prywatne wątki bez utraty danych.
- **Na żywo**: zapis wiadomości członka i odpowiedzi asystenta publikuje sygnał `chat_changed` w istniejącym strumieniu `/api/list/events` (LISTEN/NOTIFY) — pozostali domownicy pobierają wątek od razu.
- **Kontekst modelu**: ostatnie wiadomości wątku gospodarstwa (te same 20, najwyżej z ostatnich 24 h), wiadomości członków z imieniem autora („Ala: kup mleko”), odpowiedzi asystenta ze znacznikiem adresata („[do: Ala] …”); historia kończy się na bieżącej wiadomości autora. Imiona zamiast loginów także w liście przekazywanej modelowi (`requested_by`, `shopping_now`).
- **Potwierdzenia** („czy mam dodać?”, „zakończyć zakupy?”) może dać tylko autor prośby; oczekująca akcja dalej jest przypisana do autora, a wiadomości innych domowników jej nie zużywają.
- **Asystent odpowiada na każdą wiadomość** (MVP); akcje na liście są przypisane do autora wiadomości, jak dotąd. Ryzyko limitu Groq (ok. 7k tokenów na wymianę, 200k dziennie) — follow-up „tylko na @Kupto”.
- **„Wyczyść historię czatu” → „Ukryj historię u siebie”**: `DELETE /api/chat/messages` nie usuwa już wiadomości, tylko ukrywa dotychczasowe u wywołującego; pozostali domownicy i model widzą je dalej.
- **UI**: dymki z imieniem autora i godziną (strefa przeglądarki), własne po prawej, odpowiedzi asystenta oznaczone „Asystent”; tytuł czatu = nazwa gospodarstwa; pole „Imię” w rejestracji i na profilu.
- **Push** („X idzie na zakupy”, „X: zakupy zakończone”) używa imienia zamiast loginu.
- Poza zakresem: logowanie e-mailem (#77), imiona w pozostałych widokach (lista, historia, przepisy — przejdą na imię razem z #77), adresowanie asystenta („@Kupto”), strumieniowanie cudzej odpowiedzi asystenta na żywo.

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `needs-chat`: prywatna historia zastąpiona wątkiem gospodarstwa; wiadomości na żywo; potwierdzenia tylko od autora prośby; ukrycie historii u siebie.
- `user-accounts`: wymagane imię przy rejestracji, edycja imienia, uzupełnienie imienia w istniejących kontach; imię w profilu.

## Impact

- **Backend**: `models.py` (`User.name`, `User.chat_hidden_before`, `ChatMessage.private`), migracja `0012`, `auth/router.py` (imię, `PATCH /api/users/me`), `chat/router.py` (wątek gospodarstwa, sygnały, ukrywanie), `chat/prompt.py` (imiona w historii, zasada potwierdzeń), `chat/tools.py` (imiona w liście dla modelu), `lists/events.py` i `lists/router.py` (rodzaj sygnału `chat`), `lists/notifications.py` (imię w push), `config.py` (`chat_history_max_age_hours`).
- **Frontend**: `auth/AuthForm.tsx` (pole „Imię”), nowy ekran uzupełnienia imienia w `App.tsx`, `profile/ProfilePage.tsx` (edycja imienia), `chat/ChatView.tsx` (dymki z autorem i godziną, odświeżanie na żywo), `api/listEvents.ts` (`chat_changed`), `layout/ChatOptions.tsx` (ukrycie u siebie), `chat/chatTitle.ts`.
- **API**: zmiana kształtu `GET /api/chat/messages` i znaczenia `DELETE /api/chat/messages`; `POST /api/auth/register` wymaga `name`; nowe `PATCH /api/users/me`.
- **Koszty LLM**: kontekst modelu rośnie o imiona (kilka tokenów na wiadomość), ale limit 20 wiadomości i okno 24 h trzymają go w ryzach; w grupie każda wiadomość domownika wywołuje model — zob. ryzyka w design.
- **Ewaluacje**: scenariusze czatu grupowego dopisane w `backend/evals`, przebieg `-m llm` do wykonania przed merge (limit Groq wyczerpany).
