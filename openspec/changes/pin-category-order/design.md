# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/shopping-list/spec.md`.

Stan obecny, który wpływa na podejście:

- `GET /api/list` zwraca `ListOut` z grupami w kolejności enuma `Category` (`kupto.lists.schemas.list_out`); ta sama funkcja służy narzędziu `get_list` czatu. Każda mutacja listy zwraca cały `ListOut`, a frontend wpisuje go do cache TanStack Query (`keys.list`).
- Frontend odpytuje listę co 5 s (`LIST_POLL_MS`); `ListView` renderuje grupy jako `<h3>` + `<ul>`. Odhaczanie jest optymistyczne (`onMutate` + rollback).
- Zbiór kategorii jest stały (10 wartości, enum `category` w Postgresie). Użytkownik należy do co najwyżej jednego gospodarstwa, a lista pokazuje tylko niepuste kategorie.
- Aplikacja jest używana głównie na telefonach (Android, iPhone), w sklepie, często jedną ręką.
- Przyszłe zmiany, które ten projekt musi umożliwić: wyuczona kolejność kategorii i produktów (#38, przypięcia mają pierwszeństwo) oraz ręczna kolejność produktów w kategorii (#34, ten sam gest przeciągania).

## Goals / Non-Goals

**Goals:**

- Jedno miejsce w backendzie, które wylicza kolejność kategorii użytkownika z przypięć i kolejności bazowej, tak by #38 podmieniło tylko kolejność bazową.
- Przeciąganie odporne na przypadkowe gesty w sklepie (przytrzymanie na dotyku), dostępne z klawiatury.
- Natychmiastowa reakcja UI po upuszczeniu (optymistycznie), niezależnie od pollingu.

**Non-Goals:**

- Kolejność produktów w kategorii (#34) i nauka kolejności (#38).
- Kolejność per sklep (różne układy różnych sklepów) — jedna kolejność na użytkownika.
- Uwzględnianie kolejności użytkownika w odpowiedziach asystenta czatu.

## Decisions

### D1. Model danych: przypięcie = kategoria + numer miejsca w pełnej kolejności

Nowa tabela `user_category_pins`:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `user_id` | FK `users.id`, `ON DELETE CASCADE` | część PK |
| `category` | enum `category` (istniejący typ) | część PK |
| `position` | `smallint` | indeks miejsca 0…9 w pełnej kolejności wszystkich kategorii; `UNIQUE (user_id, position)` |

Brak wiersza = kategoria nieprzypięta. Kolejność użytkownika wylicza czysta funkcja `arrange(base, pins)` w nowym module `kupto.lists.ordering`: bierze nieprzypięte elementy w kolejności bazowej i wstawia przypięte w rosnącej kolejności `position` na indeks `min(position, len(wynik))`. Przy pełnym zbiorze kategorii przypięte stoją dokładnie na swoich miejscach, a nieprzypięte wypełniają luki w kolejności bazowej — to jest „przypięte mają pierwszeństwo, reszta układa się wokół”. Kolejność bazowa to dziś `list(Category)`; w #38 będzie to kolejność wyuczona (z zimnym startem), podana do tej samej funkcji.

Przypięcie przechowuje **miejsce w pełnej kolejności** (łącznie z kategoriami chwilowo pustymi), a nie pozycję na widocznej liście, bo widoczny zbiór grup zmienia się z każdym dodaniem i zakończeniem zakupów; miejsce w pełnym, stałym zbiorze jest stabilne.

`arrange` jest generyczna (dowolne hashowalne elementy) i z obcinaniem do długości działa także dla zbiorów zmiennej wielkości — #34 może jej użyć dla produktów (klucz: znormalizowana nazwa), z własną tabelą przypięć produktów.

*Alternatywy:* (a) przechowywanie całej listy kategorii użytkownika jako tablicy — nie odróżnia przypiętych od „przypadkiem leżących” tam, więc po wejściu kolejności wyuczonej nie dałoby się ułożyć reszty wokół przypięć; (b) pozycje ułamkowe / rangi leksykograficzne względem sąsiadów — przydatne przy długich, często edytowanych listach, tu zbędne przy 10 elementach i nie mają naturalnego znaczenia „to miejsce” w połączeniu z kolejnością wyuczoną; (c) kolumna JSON na `users` — prostsza migracja, ale bez więzów integralności i bez łatwej drogi do analogicznej tabeli dla produktów.

### D2. Przeniesienie: operacja względem sąsiadów, przeliczenie wszystkich przypięć

`PUT /api/list/category-order/{category}` z treścią `{"after": Category | null, "before": Category | null}` — sąsiedzi upuszczonej kategorii na widocznej liście klienta. Serwer:

1. wylicza bieżącą pełną kolejność `arrange(base, pins)` i usuwa z niej przenoszoną kategorię,
2. wstawia ją: na początek, gdy `after` jest `null`; na koniec, gdy `before` jest `null`; w przeciwnym razie bezpośrednio za `after`,
3. zapisuje jako przypięte: przenoszoną kategorię i wszystkie wcześniej przypięte, każdą z jej nowym indeksem w tej kolejności (usunięcie i wstawienie wierszy w jednej transakcji).

Krok 3 zachowuje względny układ wcześniejszych przypięć (przesuwają się o jedno miejsce, jeśli nowa kategoria wskoczyła przed nie), a nieprzypięte nadal leżą w kolejności bazowej, więc `arrange` odtwarza dokładnie kolejność z kroku 2.

Skrajne miejsca na widocznej liście znaczą „bezwzględnie pierwsza/ostatnia”, a nie „przed/za aktualnym sąsiadem” — inaczej kategoria przypięta „na górze” spadałaby pod pustą dotąd kategorię, gdy ta dostanie pozycję (np. Chemia przeniesiona przed Pieczywo stałaby za Warzywami po dodaniu jabłek). Sąsiedzi zamiast indeksu na widocznej liście, bo klient i serwer mogą się różnić widocznym zbiorem grup (polling co 5 s), a nazwane kategorie są jednoznaczne. Sąsiad równy przenoszonej kategorii → 400 (`DomainError`); niespójnych sąsiadów (np. nieaktualny widok) serwer nie odrzuca — rozstrzyga `after`.

Przypięcia są zmieniane pod blokadą wiersza użytkownika (`SELECT … FOR UPDATE` na `users`), aby dwa równoległe przeniesienia tego samego użytkownika (np. dwa urządzenia) nie złamały `UNIQUE (user_id, position)`.

Pozostałe endpointy (wszystkie wymagają gospodarstwa, jak reszta `/api/list`):

- `DELETE /api/list/category-order/{category}` — odpięcie; pozostałe przypięcia zostają na swoich miejscach.
- `DELETE /api/list/category-order` — przywrócenie automatycznej kolejności (usunięcie wszystkich przypięć użytkownika).
- `GET /api/list/category-order` — pełna kolejność wszystkich kategorii z polem `pinned` (także pustych, których lista nie pokazuje).

Mutacje zwracają `ListOut`, jak pozostałe mutacje listy, więc frontend nie potrzebuje osobnego zapytania.

### D3. Kolejność w odpowiedzi listy, a nie osobno na kliencie

`GET /api/list` (i odpowiedzi mutacji) zwraca grupy już uporządkowane według zalogowanego użytkownika i z polem `pinned` w każdej grupie; `list_out` przyjmuje opcjonalną kolejność i zbiór przypiętych (domyślnie kolejność automatyczna — z tego korzysta czat). Dzięki temu logika kolejności (a w #38 nauki) jest tylko w backendzie, a frontend renderuje grupy w otrzymanej kolejności.

*Alternatywa:* frontend pobiera kolejność osobno i sortuje — dwa źródła prawdy i dwa zapytania przy każdym odświeżeniu; odrzucone.

### D4. Biblioteka przeciągania: `@dnd-kit/core` + `@dnd-kit/sortable`

Wymagania: dotyk na Androidzie i iOS Safari z aktywacją po przytrzymaniu, możliwość przewijania listy palcem po nagłówkach, obsługa klawiatury i czytników ekranu, zgodność z React 19, mały rozmiar, ten sam mechanizm później dla produktów w grupie (#34: wiele `SortableContext`).

`@dnd-kit` spełnia je wprost: `TouchSensor` z `activationConstraint: { delay, tolerance }` daje „przeciągnij po przytrzymaniu”, a przesunięcie palca przed upływem opóźnienia anuluje aktywację i zostawia przewijanie przeglądarce; `KeyboardSensor` z `sortableKeyboardCoordinates` i komunikaty `accessibility.announcements` (po polsku) dają dostępność; działa na zdarzeniach wskaźnika/dotyku, a nie na natywnym HTML5 DnD, które na iOS jest ograniczone. Peer dependency `react >= 16.8`, mały rozmiar, a jedyne zależności tranzytywne to własne pakiety `@dnd-kit/*` i `tslib`.

*Alternatywy:*
- `react-beautiful-dnd` — zarchiwizowane, bez wsparcia React 18+.
- `@hello-pangea/dnd` (fork powyższego) — dobra obsługa dotyku z przytrzymaniem, ale cięższe, z narzuconą strukturą „listy kolumn” i mniejszą kontrolą nad czujnikami.
- `@atlaskit/pragmatic-drag-and-drop` — oparte na natywnym HTML5 DnD; na urządzeniach dotykowych zachowanie (przytrzymanie, podgląd, przewijanie) zależy od przeglądarki i jest trudne do dostrojenia.
- SortableJS (+ wrapper React) — imperatywna manipulacja DOM w konflikcie z renderowaniem Reacta.
- `@dnd-kit/react` (nowa generacja) — wciąż w wersjach 0.x; dla stabilności wybrano dojrzałe `@dnd-kit/core` 6.x.

### D5. Gest i UI

- Uchwytem jest wiersz nagłówka kategorii (nazwa + znacznik 📌). Czujniki: `TouchSensor` `{ delay: 400, tolerance: 8 }` (przytrzymanie ~0,4 s, drobne drżenie palca dozwolone), `MouseSensor` `{ distance: 8 }` (na komputerze wystarczy pociągnąć), `KeyboardSensor` (Spacja/strzałki/Spacja).
- Nagłówek ma `touch-action: manipulation` (przewijanie nadal działa) i `user-select: none` / `-webkit-touch-callout: none`, żeby przytrzymanie na iOS nie zaznaczało tekstu ani nie otwierało menu.
- Przesuwana jest cała grupa (nagłówek z pozycjami), ruch ograniczony do osi pionowej prostym modyfikatorem; przeciągana grupa jest wyróżniona.
- Po upuszczeniu: optymistycznie przestawione grupy w cache z `pinned: true` dla przeniesionej, potem `PUT`; odpowiedź zastępuje cache, błąd przywraca poprzedni stan (wzorzec jak przy odhaczaniu). Wyliczenie sąsiadów z wyniku upuszczenia to czysta funkcja testowana jednostkowo.
- Przy przypiętej grupie: znacznik 📌 i przycisk „Odepnij” (poza obszarem uchwytu, żeby Enter/Spacja na przycisku nie zaczynały przeciągania z klawiatury). W pasku narzędzi: „Przywróć kolejność” (podpowiedź: „Przywróć automatyczną kolejność kategorii”, krótki napis mieści się na wąskim ekranie obok „Zakończ zakupy”), z potwierdzeniem jak przy kończeniu zakupów, gdy którakolwiek widoczna grupa jest przypięta.

## Risks / Trade-offs

- [Polling co 5 s podmienia dane w trakcie przeciągania] → optymistyczna aktualizacja anuluje trwające zapytania (`cancelQueries`) przy upuszczeniu; zmiana zawartości w trakcie samego gestu tylko przerysowuje grupy, które `@dnd-kit` ponownie mierzy.
- [Długie grupy przeciągane w całości są nieporęczne na małym ekranie] → przy dzisiejszych listach (kilka–kilkanaście pozycji) akceptowalne; jeśli w praktyce przeszkadza, można zwijać grupy na czas przeciągania bez zmian w API.
- [Przycisk resetu jest pokazywany tylko, gdy przypięta jest jakaś widoczna grupa] → przypięcia pustych kategorii nadal wpływają tylko na ich własne miejsca; pełny stan jest dostępny przez `GET /api/list/category-order`.
- [Testy jsdom nie odtworzą gestu dotykowego (brak geometrii elementów)] → logika upuszczenia jest czystą funkcją z testami jednostkowymi, endpointy mają testy API, a gest sprawdzany jest ręcznie w przeglądarce.

## Migration Plan

Migracja Alembic `0002` tworzy tabelę `user_category_pins` (z istniejącym typem enum `category`, bez jego ponownego tworzenia); `downgrade` ją usuwa. Zmiana API jest addytywna (nowe pole `pinned`, nowe endpointy), więc kolejność wdrożenia backendu i frontendu jest dowolna; bez przypięć lista wygląda jak dotąd.
