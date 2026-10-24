# Proposal

## Why

Pasek nawigacji urósł razem z aplikacją: „Kupto”, Przepisy, Historia, nazwa gospodarstwa, login i „Wyloguj” w jednym nagłówku. Na telefonie (320–430 px) linki zawijają się do drugiego, a czasem trzeciego wiersza i zabierają miejsce czatowi i liście. Każda kolejna strona (plan obiadów z #47) dokładałaby następny link. #80 upraszcza pasek do trzech elementów: „Kupto”, tytuł czatu i ikona profilu. Czat grupowy (#78) nie jest jeszcze gotowy — tytułem czatu jest na razie nazwa gospodarstwa, a podpięcie nazwy czatu grupowego ma wymagać zmiany w jednym miejscu.

## What Changes

- Pasek nawigacji w jednym wierszu: „Kupto” (powrót do głównego widoku), tytuł czatu (przycisk otwierający opcje czatu) i ikona profilu (link do `/profile`, etykieta „Profil”, cel dotyku ≥ 44 px). Długi tytuł skraca się wielokropkiem zamiast zawijać pasek lub poszerzać stronę.
- Tytuł czatu z jednej funkcji `chatTitle(profile)` — dziś nazwa gospodarstwa; po #78 nazwa czatu grupowego.
- Opcje czatu (arkusz otwierany tytułem): „Wyczyść historię czatu” (przeniesione z nagłówka czatu, teraz z potwierdzeniem) i link „Gospodarstwo i domownicy”. Listy wielu rozmów („historii czatów”) nie ma — backend przechowuje jeden wątek na użytkownika w gospodarstwie — więc arkusz daje dostęp do tego, co istnieje dziś.
- Nowa strona profilu `/profile`: login, nazwa gospodarstwa i linki: Gospodarstwo (domownicy, preferencje, powiadomienia), Historia zakupów, Przepisy, Plan obiadów (`/meal-plan`, trasa z #47 / PR #89) oraz „Wyloguj”.
- Wszystkie dotychczasowe elementy paska mają nowe miejsce: Przepisy, Historia, nazwa gospodarstwa (link do gospodarstwa), login i „Wyloguj” — na profilu; nazwa gospodarstwa także jako tytuł czatu.
- Poza zakresem: czat grupowy i lista rozmów (#78), zmiany backendu, migracje.

## Capabilities

### New Capabilities

- `app-navigation`: pasek nawigacji, opcje czatu i strona profilu.

### Modified Capabilities

_(brak)_

## Impact

- **Frontend**: `layout/MainPage.tsx` i `MainPage.module.css` (nowy pasek), nowe `layout/ChatOptions.tsx`, `chat/chatTitle.ts`, `profile/ProfilePage.tsx`; trasa `/profile` w `App.tsx`; przycisk czyszczenia znika z `chat/ChatView.tsx`; `layout/viewport.test.ts` pilnuje paska w jednym wierszu.
- **Backend**: bez zmian, bez migracji.
- **Zależności**: link „Plan obiadów” prowadzi do trasy dodawanej w PR #89 — tę zmianę mergujemy po nim. Docelowy tytuł czatu zależy od #78.
