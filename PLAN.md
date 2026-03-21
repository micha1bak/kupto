# Plan Refaktoryzacji Kupto: v1.0 -> v2.0 (Next.js)

Cel: Przeniesienie logiki z czystego JavaScriptu i Node.js (v1.0) na nowoczesny stos technologiczny Next.js (v2.0), zachowując i ulepszając istniejące funkcjonalności.

## 1. Architektura i Technologie
- **Framework**: Next.js 15 (App Router).
- **Język**: TypeScript (zamiast JS).
- **Stylizacja**: Tailwind CSS (zamiast style.css).
- **Baza danych**: PostgreSQL (Docker).
- **Autoryzacja**: JWT (biblioteka `jose`), przechowywane w ciasteczkach **HTTP-only** (bezpieczniejsze niż LocalStorage).
- **Komunikacja**: Server Actions (zamiast REST API fetch).

## 2. Etapy Implementacji

### Etap 1: Fundamenty i Baza Danych (Zakończone/W trakcie)
- [x] Konfiguracja `docker-compose.yml` dla PostgreSQL.
- [x] Konfiguracja zmiennych środowiskowych (`.env.local`).
- [x] Implementacja singletona połączenia z bazą (`lib/db.ts`).
- [ ] Odtworzenie schematu bazy danych:
    - Tabele: `users`, `category`, `product`, `shopping_list`.
    - Widoki pomocnicze: `full_shopping_list`, `prod_cat`.

### Etap 2: Autoryzacja i Sesja
- [x] Narzędzia JWT w `lib/auth.ts`.
- [ ] Implementacja **Middleware** (`middleware.ts`) do ochrony tras przed niezalogowanymi użytkownikami.
- [ ] Refaktoryzacja `app/login/page.tsx` i `LoginForm.tsx`:
    - Podpięcie Server Action do weryfikacji hasła (v1.0 używa czystego tekstu - docelowo do zmiany na `bcrypt`).
    - Ustawianie ciasteczka z tokenem po poprawnym logowaniu.
- [ ] Implementacja wylogowania (usuwanie ciasteczka).

### Etap 3: Główna Lista Zakupów (Core)
- [x] Implementacja wczytywania listy z bazy:
    - [x] Server Action `getShoppingList` (pobieranie produktów zalogowanego użytkownika).
    - [x] Grupowanie danych po kategorii na serwerze.
    - [x] Testy jednostkowe dla akcji pobierania.
    - [x] Podpięcie akcji do `app/page.tsx` i `ShoppingList.tsx`.
- [ ] Implementacja Server Action `deleteItemFromList`:
    - Usuwanie rekordu z `shopping_list`.
    - Odświeżanie UI za pomocą `revalidatePath`.
- [ ] Implementacja Server Action `updateItemQuantity`:
    - Dodanie możliwości zmiany ilości bezpośrednio na liście.

## 4. Szczegółowy Plan: Wczytywanie listy zakupów (Dzisiaj)
1. **Warstwa danych (Server Action):**
   - Plik: `app/actions/shopping-list.ts`.
   - Funkcja `getShoppingList()`: pobieranie `userId` z sesji, SQL join (`list_item` + `product` + `category`), formatowanie do struktury grupowej.
2. **Integracja z UI:**
   - `app/page.tsx`: Zmiana na asynchroniczny Server Component, pobranie danych.
   - `app/ui/ShoppingList.tsx`: Przyjmowanie danych przez propsy zamiast `MOCK_DATA`.
3. **Testy:**
   - Plik: `app/actions/shopping-list.test.ts`.
   - Scenariusze: poprawne mapowanie, brak sesji, pusta lista.
4. **Weryfikacja:** `npm test` + manualne sprawdzenie z Dockerem.

## 5. Mapowanie Funkcji v1.0 -> v2.0
- [ ] Refaktoryzacja `SearchBar.tsx`:
    - Implementacja podpowiedzi (suggestions) pobieranych z tabeli `product`.
    - Dodawanie wybranego produktu do listy (`addItemToList`).
- [ ] Implementacja Modala "Nowy Produkt":
    - Pobieranie listy kategorii z bazy.
    - Dodawanie nowego produktu do bazy (`addNewProduct`).
    - Walidacja danych (np. formatowanie nazwy: pierwsza duża litera).

### Etap 5: Real-time i UX (Ulepszenia)
- [ ] **Optimistic Updates**: Użycie `useOptimistic` przy usuwaniu i dodawaniu produktów, aby UI reagował natychmiastowo.
- [ ] **Skeleton Screens**: Wyświetlanie placeholderów podczas ładowania listy.
- [ ] **WebSockets (Opcjonalnie)**: Rozważenie `Pusher` lub `Supabase Realtime` dla synchronizacji między użytkownikami w czasie rzeczywistym (zgodnie z TODO w v1.0).

### Etap 6: Deployment i Docker
- [ ] Stworzenie `Dockerfile` zoptymalizowanego pod Next.js.
- [ ] Konfiguracja skryptów wdrożeniowych na VPS.

## 3. Mapowanie Funkcji v1.0 -> v2.0

| Funkcja v1.0 | Implementacja v2.0 |
| :--- | :--- |
| `GET /api/list` | Server Component + `query('SELECT * FROM full_shopping_list')` |
| `POST /api/login` | Server Action `login(formData)` |
| `POST /api/list` | Server Action `addItemToList(productId, quantity)` |
| `DELETE /api/list/:id` | Server Action `deleteItem(id)` |
| `app.js` (DOM Manipulation) | React State + Server Actions |
| `style.css` | Tailwind Utility Classes |

## 4. Bezpieczeństwo
- Przejście na haszowanie haseł (np. `argon2` lub `bcrypt`).
- CSRF protection (automatyczne w Server Actions).
- Walidacja wejścia (np. biblioteka `zod`).
