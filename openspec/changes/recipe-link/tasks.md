# Tasks

## 1. Pobieranie strony (spec: needs-chat — Bezpieczne pobieranie stron z przepisami)

- [x] 1.1 `kupto/recipes/fetch.py`: walidacja adresu, publiczne adresy po DNS, połączenie na sprawdzony IP z `Host`/SNI, przekierowania, limity czasu i rozmiaru, tylko HTML (D4); `httpx` w zależnościach aplikacji
- [x] 1.2 Testy bez sieci (`MockTransport`, podstawiony resolver): adresy prywatne/lokalne/metadane, IPv4 w IPv6, nazwa z adresem prywatnym, przekierowania do zabronionych celów, pętla przekierowań, limit rozmiaru, limit czasu, nie-HTML, kodowanie

## 2. Wyciąganie przepisu (spec: needs-chat — Przepis z linku)

- [x] 2.1 `kupto/recipes/extract.py`: JSON-LD `Recipe` (`@graph`, listy typów), tekst strony z oknem przy „Składniki” (D2, D3); `service.py` z wynikiem dla modelu (D1)
- [x] 2.2 Testy: JSON-LD w `@graph`, błędny JSON-LD → tekst, długa strona z menu, wynik `recipe_from_url`

## 3. Czat

- [x] 3.1 Narzędzie `fetch_recipe` (tylko odczyt) i zasada 4b w prompcie (D1, D5); testy narzędzia i promptu
- [x] 3.2 Ewaluacje: link z JSON-LD → propozycja bez zmiany listy, potwierdzenie → tylko brakujące z „na: <danie>”; strona bez JSON-LD (z ukrytym poleceniem) → propozycja z tekstu, lista bez zmian; link do adresu prywatnego → prośba o wklejenie

## 4. Integracja

- [x] 4.1 Kroki CI lokalnie: backend `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`; frontend `npm ci`, `npx tsc -b`, `npm test`, `npx vite build`
