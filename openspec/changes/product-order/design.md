# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/shopping-list/spec.md`.

Stan obecny, który wpływa na podejście:

- #33 dodał przypięcia kategorii per użytkownik (`user_category_pins`, `kupto.lists.category_order`) i generyczną funkcję `arrange(base, pins)` w `kupto.lists.ordering`: przypięcie to numer miejsca w pełnej kolejności. Dla kategorii ten zbiór jest stały (10 wartości enuma), więc numer miejsca jest stabilny.
- `list_out` układa grupy według kolejności kategorii użytkownika, a pozycje w grupie alfabetycznie po `normalized_name`. Ta sama funkcja z domyślną kolejnością służy czatowi.
- Pozycja listy (`ListItem`) znika przy zakończeniu zakupów; ten sam produkt wraca jako nowa pozycja z tą samą znormalizowaną nazwą (unikalną w obrębie listy). Kategoria pozycji może się zmienić (np. z „Inne” na właściwą przy kolejnym zgłoszeniu).
- Lista na żywo (#26): zmiana kolejności publikuje `events.order_changed(session, user)` przed commitem — sygnał dociera tylko do strumieni tego użytkownika.
- Frontend: `ListView` z `@dnd-kit` — grupy są elementami jednego `SortableContext`, uchwytem jest nagłówek (`setActivatorNodeRef`), `TouchSensor` z przytrzymaniem 400 ms. Wiersz pozycji ma pole wyboru „Kupione”, nazwę z zapotrzebowaniami i przycisk usuwania.
- Przyszłość: #38 — kolejność wyuczona z historii zakupów dla nieprzypiętych kategorii i produktów.

## Goals / Non-Goals

**Goals:**

- Kolejność produktów zapamiętana per użytkownik i per produkt, działająca przy kolejnym dodaniu produktu.
- Przypięcia, które zachowują intencję użytkownika („ser za jogurtem”, „jogurt na końcu”) także wtedy, gdy zmienia się zestaw produktów na liście.
- Jedno miejsce z kolejnością bazową produktów, które #38 podmieni na wyuczoną.
- Przeciąganie wiersza, które nie koliduje z odhaczaniem, przewijaniem i przeciąganiem kategorii.

**Non-Goals:**

- Przenoszenie produktu do innej kategorii przeciąganiem.
- Kolejność wyuczona (#38), kolejność per sklep.
- Przycisk „przywróć alfabetyczną kolejność” dla całej kategorii (odpinanie pojedynczo wystarcza; endpoint łatwo dodać później).
- Kolejność użytkownika w odpowiedziach czatu.

## Decisions

### D1. Przypięcie produktu jest w obrębie kategorii

Przypięcie zapamiętuje kategorię, w której produkt został ułożony, i porządkuje go tylko względem produktów tej kategorii. Grupy kategorii mają już własną kolejność (#33), a produkt przeciąga się tylko w obrębie swojej grupy, więc globalna pozycja produktu na całej liście nie miałaby znaczenia i psułaby się przy każdym przestawieniu kategorii.

Gdy produkt pojawi się w innej kategorii niż ta z przypięcia (np. przeszedł z „Inne” do „Nabiał”), przypięcie go nie dotyczy: produkt stoi w kolejności bazowej nowej kategorii i nie ma znacznika. Przypięcie zostaje w bazie (wróci do gry, gdy produkt wróci do tamtej kategorii) i jest zastępowane przy pierwszym przypięciu produktu w nowej kategorii — jeden produkt ma u użytkownika najwyżej jedno przypięcie.

### D2. Model danych: przypięcie zakotwiczone za sąsiadem, a nie numer miejsca

Numer miejsca (jak dla kategorii) nie działa dobrze dla produktów, bo zbiór produktów w kategorii stale się zmienia. Przykład: „ser” ułożony między „jogurtem” a „mlekiem” (miejsce 1); gdy pojawi się „bita śmietana”, miejsce 1 to już pozycja przed „jogurtem”. „Jogurt” przeciągnięty na koniec (miejsce 2 z 3) przestaje być ostatni, gdy dojdzie „twaróg”.

Dlatego przypięcie produktu zapamiętuje **kotwicę** — nieprzypięty produkt, za którym stoi (albo początek / koniec kategorii) — i **rangę** porządkującą przypięte produkty między sobą. Nowa tabela `user_product_pins`:

| Kolumna | Typ | Uwagi |
|---|---|---|
| `user_id` | FK `users.id`, `ON DELETE CASCADE` | część PK |
| `normalized_name` | `varchar(100)` | część PK — klucz produktu, jak `ListItem.normalized_name` |
| `category` | enum `category` (istniejący typ) | kategoria, w której przypięto |
| `after_name` | `varchar(100) NULL` | znormalizowana nazwa nieprzypiętego produktu bezpośrednio przed przypiętym; `NULL` = początek kategorii |
| `at_end` | `boolean NOT NULL DEFAULT false` | przypięty na końcu kategorii (wtedy `after_name` jest `NULL`) |
| `position` | `smallint` | ranga wśród przypięć użytkownika w kategorii; `UNIQUE (user_id, category, position)` |

Wyliczenie kolejności — czysta funkcja `arrange_anchored(base, pins)` w `kupto.lists.ordering`: bierze nieprzypięte elementy w kolejności bazowej, za każdym wstawia przypięte z tą kotwicą (rosnąco po randze), przypięte z kotwicą „początek” daje na początek, „koniec” — na koniec. Przypięcie z kotwicą, której nie ma wśród nieprzypiętych (stan, który serwis nie powinien zostawić), trafia przed grupę „koniec”, więc żaden element nie ginie.

Zbiór, który się układa (dla kategorii C): produkty obecne na liście w C ∪ produkty przypięte w C ∪ ich kotwice. Nieobecne produkty biorą udział tylko w ustaleniu względnego układu i są odfiltrowywane przed zwróceniem listy — dlatego przypięte „ser, mleko, jogurt” dają „ser, jogurt”, gdy „mleka” chwilowo nie ma, a kotwica, której nie ma na liście, nadal wyznacza miejsce w kolejności bazowej.

Kolejność bazowa: `product_base_order(category, names)` w nowym module `kupto.lists.product_order` — dziś `sorted(names)` (alfabetycznie po znormalizowanej nazwie, jak dotąd). **Podpięcie #38**: ta funkcja zwróci kolejność wyuczoną dla danego zbioru nazw (z zimnym startem alfabetycznym), a `arrange_anchored` ułoży wokół niej przypięcia bez zmian w modelu ani w API; kotwice są nazwami produktów, więc znaczą to samo przy każdej bazie.

*Alternatywy:* (a) `arrange` z numerem miejsca w pełnej kolejności (jak kategorie) — prostsze, ale przypięcia „pływają” przy każdym nowym produkcie (przykłady wyżej); (b) numer miejsca liczony w zbiorze wszystkich znanych produktów gospodarstwa (`household_products`) — stabilniejszy, ale zbiór jest per gospodarstwo, a przypięcia per użytkownik, nie każdy produkt trafia do pamięci kategorii, a nowe produkty i tak przesuwają numery; (c) przypięcie całej widocznej kolejności kategorii przy każdym przeciągnięciu — znika rozróżnienie przypięte/nieprzypięte potrzebne #38 i znacznik 📌 byłby przy wszystkim; (d) pozycje ułamkowe względem sąsiadów — rozwiązują wstawianie między, ale nie mają znaczenia przy innej bazie (#38) i nie wyrażają „na końcu”.

### D3. Przeniesienie: operacja względem sąsiadów, przeliczenie przypięć kategorii

`PUT /api/list/items/{item_id}/order` z treścią `{"after": item_id | null, "before": item_id | null}` — sąsiedzi upuszczonej pozycji w jej grupie na liście klienta. Serwer (pod blokadą wiersza użytkownika, jak przy kategoriach):

1. Szuka pozycji w liście gospodarstwa (404). Sąsiedzi z innej kategorii albo równi przenoszonej pozycji → 400. Sąsiad, którego już nie ma na liście (np. ktoś go właśnie usunął), jest pomijany (krok 3).
2. Wylicza pełną kolejność F kategorii (`arrange_anchored`, zbiór z D2 poszerzony o sąsiadów), zapamiętuje najbliższy nieprzypięty element przed produktem (jego „stare miejsce”) i wyjmuje produkt.
3. Wstawia go jak przy kategoriach (skrajne miejsca na liście klienta znaczą bezwzględnie pierwszy/ostatni): bez `after` — na początek; z `after`, ale bez `before` — na koniec; w przeciwnym razie bezpośrednio za `after`, a gdy tej pozycji już nie ma — bezpośrednio przed `before`; gdy nie ma żadnego z sąsiadów → 409 (widok klienta jest nieaktualny, klient pobiera listę ponownie).
4. Nowe przypięcie produktu: na końcu → `at_end`; w pozostałych przypadkach kotwica = najbliższy nieprzypięty element przed nim w nowej kolejności (albo początek). Przypięcia zakotwiczone za przenoszonym produktem (był nieprzypięty) dostają jego stare miejsce z kroku 2. Rangi wszystkich przypięć kategorii = ich kolejność w nowej F. Zapis: usunięcie przypięć użytkownika w tej kategorii oraz przypięcia tego produktu w innej kategorii, wstawienie nowych — w jednej transakcji, z `order_changed` przed commitem.

Krok 4 zachowuje względny układ wcześniejszych przypięć, a `arrange_anchored` z nowymi przypięciami odtwarza dokładnie nową kolejność F (test serwisu sprawdza to dla każdego scenariusza).

`DELETE /api/list/items/{item_id}/order` — odpięcie produktu tej pozycji; pozostałe przypięcia zostają (przypięcia zakotwiczone za nim nadal mają poprawną kotwicę, bo po odpięciu jest on nieprzypięty). Oba endpointy zwracają `ListOut`, jak pozostałe mutacje listy. Identyfikatory pozycji zamiast nazw w URL, bo klient zna `id`, a nazwy produktów mają spacje i polskie znaki; serwer sam przechodzi na `normalized_name`.

### D4. Kolejność w odpowiedzi listy

`list_out` dostaje opcjonalną kolejność produktów (`ProductOrder` — przypięcia użytkownika pogrupowane po kategorii; domyślnie pusta → kolejność bazowa, z której korzysta czat) i układa pozycje każdej grupy przez `ProductOrder.arrange(category, items)`. `ItemOut` dostaje pole `pinned` (produkt ma przypięcie w kategorii pozycji). Odczyt przypięć to jedno zapytanie na odpowiedź listy.

### D5. Frontend: zagnieżdżone sortowanie w grupie

- Każda grupa renderuje **własny** `DndContext` + `SortableContext` z identyfikatorami pozycji, wewnątrz elementu sortowalnego grupy. Osobny kontekst ogranicza przeciąganie do kategorii bez dodatkowych warunków i nie miesza identyfikatorów pozycji z kategoriami. Czujniki zewnętrznego kontekstu są podpięte tylko do uchwytu nagłówka, a wewnętrznego — tylko do uchwytu wiersza, więc gesty się nie nakładają i przeciąganie kategorii działa jak dotąd (cała grupa razem z pozycjami).
- Uchwyt: osobny element ⠿ na początku wiersza (przed polem wyboru, z dala od przycisku usuwania), z etykietą „Przenieś {produkt}”. Na dotyku przeciąganie startuje po przytrzymaniu uchwytu 400 ms (`TouchSensor { delay: 400, tolerance: 8 }`, jak nagłówki); uchwyt ma `touch-action: manipulation` i blokadę zaznaczania tekstu, więc przesunięcie palcem po nim przewija listę. Pole wyboru i reszta wiersza nie mają czujników — odhaczanie i przewijanie działają bez zmian. Mysz: `distance: 8`; klawiatura: Spacja/strzałki/Spacja; polskie komunikaty dla czytników z nazwami produktów.
- Przypięty produkt: znacznik 📌 przy nazwie i przycisk „Odepnij” w wierszu.
- Po upuszczeniu: optymistyczne przestawienie pozycji w cache z `pinned: true` dla przeniesionej, potem `PUT`; odpowiedź zastępuje cache, błąd przywraca poprzedni stan (wzorzec z `categoryOrder.ts`). Wyliczenie sąsiadów to ta sama czysta funkcja co dla kategorii, uogólniona na dowolne identyfikatory.

## Risks / Trade-offs

- [Kotwice to nazwy produktów — przypięcia „pamiętają” produkty, których dawno nie było] → to zamierzone (kolejność ma przetrwać tygodnie); liczba wierszy jest ograniczona liczbą produktów, które użytkownik kiedykolwiek przeciągnął; kaskada przy usunięciu konta.
- [Przypięcie z innej kategorii nie działa po zmianie kategorii produktu] → świadomie (D1); po przeciągnięciu w nowej kategorii stare przypięcie jest zastępowane.
- [Zagnieżdżone `DndContext` — dwa regiony komunikatów dla czytników na grupę] → komunikaty są krótkie i dotyczą tylko aktywnego przeciągania.
- [jsdom nie odtworzy gestu dotykowego] → wyliczenie upuszczenia to czysta funkcja z testami, przeciąganie z klawiatury jest testowane w Vitest, gest dotykowy wymaga ręcznego sprawdzenia na telefonie.

## Migration Plan

Migracja Alembic `0006` (`down_revision = "0005"`) tworzy tabelę `user_product_pins` (z istniejącym typem enum `category`, bez jego tworzenia); jest wyłącznie addytywna — istniejące tabele i dane bez zmian. `downgrade` usuwa tabelę (tracąc tylko ręczną kolejność produktów). Zmiana API jest addytywna (pole `pinned` w pozycjach, nowe endpointy), więc kolejność wdrożenia backendu i frontendu jest dowolna; bez przypięć lista wygląda jak dotąd.
