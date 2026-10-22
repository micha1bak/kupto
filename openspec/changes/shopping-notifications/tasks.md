# Tasks

## 1. Backend (spec: notifications)

- [x] 1.1 Moduł `kupto.lists.notifications`: treści, tagi, przycinanie nazw, grupowanie #30 (design D3, D4); weryfikacja: test `format_names`
- [x] 1.2 Wywołania po commicie w `lists/router.py` (`POST /needs`, `POST /finish`, `POST /shopping`) (design D1); weryfikacja: testy REST z atrapą transportu
- [x] 1.3 `ToolContext.notifier` i wywołania w narzędziach czatu `add_needs`, `confirm_finish_shopping`, `start_shopping` (design D2); weryfikacja: testy przez `/api/chat/messages`
- [x] 1.4 Testy: autor bez własnego powiadomienia, brak kupujących = brak #30, ponowny start = brak #29, izolacja gospodarstw, okno grupowania, zakończenie bez pozycji

## 2. Frontend

- [x] 2.1 Tekst banera instalacji na iPhonie bez „(wkrótce)”; weryfikacja: `npx tsc -b`, `npm test`

## 3. Integracja

- [x] 3.1 Kroki CI lokalnie (backend i frontend)
- [ ] 3.2 Ręcznie na produkcji: trzy powiadomienia na Androidzie i iPhonie (PWA) — poza CI

## Workflow follow-up

- Zarchiwizować po change `web-push` (który tworzy capability `notifications`) i po weryfikacji 3.2.
