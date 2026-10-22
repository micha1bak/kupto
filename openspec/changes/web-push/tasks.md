# Tasks

## 1. Backend: konfiguracja, model i migracja

- [ ] 1.1 Zależność `pywebpush` (wersje wydane ≥ 2 tygodnie temu, `uv.lock`), ustawienia `vapid_public_key` / `vapid_private_key` / `vapid_subject`, `VapidConfig.from_settings` i generator `python -m kupto.push.keys` (design D1, D2); weryfikacja: testy konfiguracji — brak kluczy, niekompletne, niepasujące, poprawne
- [ ] 1.2 Model `PushSubscription` i migracja Alembic `0005` (`down_revision = "0004"`) (design D3); weryfikacja: `tests/test_migrations.py` — upgrade z danymi i downgrade, `uv run alembic heads` = jedna głowa

## 2. Backend: API i wysyłka (spec: notifications)

- [ ] 2.1 Endpointy `/api/push/public-key`, `PUT` / `DELETE /api/push/subscriptions` z walidacją adresu i limitem urządzeń (design D3–D5); weryfikacja: testy API — 401, 404 `push_disabled`, upsert i przepięcie, cudza subskrypcja, 422
- [ ] 2.2 `Notifier` (`send_to_users`, `send_to_household`, `drain`), transport `webpush_async`, sprzątanie 404/410, `lifespan` (design D6, D7); weryfikacja: testy z atrapą transportu — adresaci, wykluczenia, 410, limit czasu, wyłączone powiadomienia

## 3. Frontend (spec: notifications)

- [ ] 3.1 `push` i `notificationclick` w `sw.ts` (design D8); weryfikacja: `npx tsc -b`, `npx vite build`
- [ ] 3.2 `pwa/push.ts` i `NotificationSettings` na stronie gospodarstwa, wyłączenie przy wylogowaniu (design D9); weryfikacja: Vitest — stany przycisku, zgoda tylko po kliknięciu

## 4. Wdrożenie i integracja

- [ ] 4.1 `VAPID_*` w `deploy/docker-compose.yml`, `.env.example`, tabela sekretów i polecenia w `deploy/README.md`; weryfikacja: `docker compose --project-directory deploy -f deploy/docker-compose.yml config` z przykładowym env
- [ ] 4.2 Kroki CI lokalnie (backend i frontend)
- [ ] 4.3 Ręcznie po wpisaniu kluczy na produkcji: włączenie na Androidzie i iPhonie (PWA), testowe powiadomienie — poza CI

## Workflow follow-up

- Po scaleniu PR i weryfikacji 4.3 zarchiwizować change (`/opsx:archive`), co utworzy `openspec/specs/notifications/spec.md`.
