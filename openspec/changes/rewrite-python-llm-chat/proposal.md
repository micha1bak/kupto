# Proposal

## Why

Obecne Kupto to klasyczny CRUD (Express + TypeScript + Prisma): użytkownik musi ręcznie wybierać produkty z katalogu, kategorie i ilości, a współdzielenie list sprowadza się do nadawania dostępu. Domownicy w praktyce zgłaszają potrzeby swobodnym językiem („skończyło się mleko”, „kup coś na śniadanie dla dzieci”), więc aplikacja powinna przyjmować je w rozmowie i sama budować wspólną listę zakupów. Przepisujemy ją w Pythonie z LLM (OpenAI) jako rdzeniem interakcji.

## What Changes

- **BREAKING** Usunięcie całej aplikacji TypeScript/Express (`src/`, `prisma/`, `package.json`, obecny frontend w `src/public/`) oraz jej REST API (`/api/list`, `/api/lists/:id/access`, `/api/products`, …).
- **BREAKING** Nowy schemat bazy danych od zera; istniejące dane (użytkownicy, listy, produkty, szablony) nie są migrowane.
- Nowy backend w Pythonie: API HTTP + strumieniowanie odpowiedzi czatu.
- Nowy frontend jako osobna aplikacja SPA, komunikująca się z backendem przez API.
- Nowy model domeny: **gospodarstwo** (grupa użytkowników) zamiast list z nadawanym dostępem; każde gospodarstwo ma jedną aktywną listę zakupów.
- Czat z asystentem LLM: użytkownik opisuje swoje potrzeby, asystent wyodrębnia produkty i ilości, dopytuje przy niejasnościach i aktualizuje wspólną listę.
- Scalanie zapotrzebowań wielu domowników: deduplikacja, sumowanie ilości, automatyczna kategoryzacja, informacja kto czego potrzebuje.
- Lista dostępna także bezpośrednio w UI (odhaczanie kupionych, usuwanie, zakończenie zakupów) bez pośrednictwa LLM.
- Limity użycia LLM (długość wiadomości, liczba wiadomości na użytkownika) chroniące przed kosztami i nadużyciami.
- Nowa konfiguracja Docker/docker-compose i aktualizacja workflow deploy na VPS (nowy sekret `OPENAI_API_KEY`).

## Capabilities

### New Capabilities

- `user-accounts`: rejestracja, logowanie, wylogowanie i sesja użytkownika.
- `households`: tworzenie gospodarstwa, zapraszanie i usuwanie członków, opuszczanie gospodarstwa; wyznacza zakres współdzielenia listy i czatu.
- `needs-chat`: rozmowa z asystentem LLM, który rozumie zgłaszane potrzeby i wykonuje na ich podstawie operacje na liście, wraz z historią rozmowy i limitami użycia.
- `shopping-list`: wspólna lista zakupów gospodarstwa budowana z zapotrzebowań członków — scalanie, kategoryzacja, przypisanie zgłaszających, odhaczanie kupionych i zakończenie zakupów.

### Modified Capabilities

<!-- Brak — projekt nie ma jeszcze żadnych specyfikacji w openspec/specs/. -->

## Impact

- **Kod**: usunięcie `src/`, `prisma/`, `prisma.config.ts`, `package.json`, `package-lock.json`, `tsconfig.json`, `jest.config.js`, `api.json`; nowe katalogi `backend/` (Python) i `frontend/` (SPA).
- **API**: całkowicie nowe API; dotychczasowi klienci (obecny frontend) przestają działać.
- **Baza danych**: PostgreSQL pozostaje, ale ze świeżym schematem zarządzanym migracjami Pythona; stare dane zostają tylko w kopii zapasowej.
- **Zależności**: Python (framework webowy, ORM, OpenAI SDK), osobny toolchain frontendu; usunięcie zależności Node backendu.
- **Usługi zewnętrzne**: OpenAI API — koszty zależne od użycia, wymagany klucz API, dane z rozmów trafiają do OpenAI.
- **Infrastruktura**: nowe Dockerfile dla backendu i frontendu, zaktualizowany `docker-compose.yml`, `.env.example` i `.github/workflows/deploy.yml`.
