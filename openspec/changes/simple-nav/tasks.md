# Tasks

## 1. Pasek nawigacji (spec: app-navigation — Pasek nawigacji)

- [x] 1.1 `chat/chatTitle.ts` (D2); nowy pasek w `MainPage.tsx` i `MainPage.module.css`: „Kupto”, tytuł czatu, ikona profilu w siatce jednego wiersza (D1, D6)
- [x] 1.2 `viewport.test.ts`: pasek w jednym wierszu, skracany tytuł, cel dotyku ikony; testy Vitest paska

## 2. Opcje czatu (spec: app-navigation — Opcje czatu)

- [x] 2.1 `layout/ChatOptions.tsx`: arkusz z wyczyszczeniem historii i linkiem do gospodarstwa; przycisk czyszczenia znika z `ChatView` (D3, D4); testy Vitest

## 3. Profil (spec: app-navigation — Strona profilu)

- [x] 3.1 `profile/ProfilePage.tsx` i trasa `/profile`: login, gospodarstwo, linki, wylogowanie (D5); testy Vitest

## 4. Integracja

- [x] 4.1 Kroki CI lokalnie: frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`; `scrollWidth` przy 375 px w przeglądarce
