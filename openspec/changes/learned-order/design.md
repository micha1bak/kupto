# Design

## Context

Motywacja: `proposal.md`. Wymagania: `specs/shopping-list/spec.md`.

Stan obecny, który wpływa na podejście:

- Kolejność kategorii użytkownika to `arrange(automatic_order(), pins)` w `kupto.lists.category_order` (#33): przypięcie to numer miejsca w pełnej kolejności 10 kategorii, a `automatic_order()` zwraca dziś `list(Category)`.
- Kolejność produktów w kategorii to `arrange_anchored(product_base_order(category, names), pins)` w `kupto.lists.product_order` (#34): przypięcie to kotwica (nieprzypięty sąsiad, początek albo koniec) i ranga; `product_base_order` sortuje dziś alfabetycznie. Obie funkcje bazowe były przygotowane jako punkt podpięcia #38.
- Historia (#36): „Zakończ zakupy” kopiuje każdą odhaczoną pozycję do `purchased_items` razem z `bought_at` i `bought_by_id` (kto i kiedy odhaczył), w obrębie nagłówka `shopping_trips` (`household_id`, `finished_at`). Indeksy: `purchased_items(trip_id)`, `purchased_items(bought_by_id)`, `shopping_trips(household_id, finished_at)`.
- Odhaczenie ustawia `bought_at = now()`; cofnięcie i ponowne odhaczenie nadpisuje czas. Odhaczenie kilku pozycji naraz (np. przez czat) daje im ten sam czas.
- Listę pobiera się często (po każdym sygnale listy na żywo), więc koszt wyliczenia kolejności ma znaczenie.

## Goals / Non-Goals

**Goals:**

- Kolejność per użytkownik z jego własnych odhaczeń, z sensownym zimnym startem.
- Kolejność stabilna: nie zmienia się w trakcie zakupów i nie skacze po pojedynczym nietypowym przejściu.
- Przypięcia działają bez zmian modelu i API, a nieprzypięte elementy układają się wokół nich według nauki.
- Prosta, opisana heurystyka bez ML, z progami jako stałymi w jednym module.

**Non-Goals:**

- Kolejność per sklep (np. rozpoznawanie, w którym sklepie odbyły się zakupy).
- Dzielenie jednego zakończenia zakupów na kilka wizyt w sklepie.
- Zmiany UI (np. wyjaśnienie, skąd wzięła się kolejność).
- Kolejność użytkownika w odpowiedziach czatu.

## Decisions

### D1. Źródło: „przejście” = odhaczenia jednego użytkownika w jednym zakończeniu zakupów

Przejście przez sklep to pozycje jednego zakończenia zakupów (`trip_id`) odhaczone przez jednego użytkownika (`bought_by_id`), uporządkowane po `bought_at` (remis — `id`, czyli kolejność kopiowania do historii). Pozycje odhaczone przez innych domowników w tym samym zakończeniu tworzą ich własne przejścia — przeplatanie odhaczeń dwóch osób w jednym sklepie nie mówi nic o kolejności półek. Przejście z mniej niż **2** pozycjami pomijamy (nie niesie informacji o kolejności).

`bought_at` i `bought_by_id` wystarczają, więc kolejności odhaczeń nie trzeba zapisywać osobno. Ograniczenia akceptujemy świadomie: odhaczenie „hurtem” po powrocie do domu albo przez czat (ten sam czas) daje przejście bez sensownej kolejności — mediana z wielu przejść (D3) tłumi taki szum.

Bierzemy wyłącznie zakończenia zakupów **bieżącego gospodarstwa** użytkownika: historia należy do gospodarstwa (tak jak w widoku historii), a zakupy w poprzednim gospodarstwie to zwykle inny sklep. Użytkownik bez gospodarstwa nie ma nauki.

### D2. Okno i zimny start

- **Własne przejścia**: ostatnie **10** przejść użytkownika (po `finished_at` zakończenia). Gdy jest ich co najmniej **3**, kolejność uczy się tylko z nich.
- **Gospodarstwo**: w przeciwnym razie — ostatnie 10 przejść wszystkich członków gospodarstwa (także użytkownika). Gdy jest ich co najmniej 3, kolejność uczy się z nich; nowy domownik od razu dostaje kolejność „domową”.
- **Bez nauki**: w przeciwnym razie kolejność bazowa jak dotąd (stała kolejność kategorii, alfabetyczna produktów).

Przejścia osób z usuniętym kontem (`bought_by_id IS NULL`) pomijamy — nie da się ich rozdzielić na osoby.

### D3. Wynik elementu: mediana względnego miejsca

W przejściu z `n` pozycjami pozycja na miejscu `i` (od 0) ma względne miejsce `i / (n − 1)` ∈ [0, 1] — dzięki temu krótkie i długie przejścia ważą tak samo.

- **Produkt** (po `normalized_name`): w przejściu — względne miejsce jego pozycji; wynik = **mediana** z przejść, w których wystąpił. Produkty porównujemy tylko w obrębie bieżącej kategorii, więc względne miejsce w całym przejściu wystarcza (kategoria z historii nie ma znaczenia — produkt mógł zmienić kategorię).
- **Kategoria**: w przejściu — średnia względnych miejsc jej pozycji (kategoria rozrzucona po sklepie, np. „Inne”, ląduje pośrodku); wynik = mediana z przejść.
- Element jest **wyuczony**, gdy wystąpił w co najmniej **2** przejściach z okna; pojedyncza obserwacja nie przestawia kolejności.

Mediana zamiast średniej, żeby jedno nietypowe przejście (inny sklep, odhaczanie w domu) nie przesuwało kolejności. Wszystkie progi to stałe w `kupto/lists/learned_order.py`.

### D4. Scalenie z kolejnością bazową: wyuczone zamieniają się miejscami

Czysta funkcja `learned(base, scores)` w `kupto.lists.ordering`: elementy wyuczone zajmują te same miejsca w kolejności bazowej co dotąd, ale ułożone między sobą rosnąco po wyniku (remis — kolejność bazowa); elementy niewyuczone zostają dokładnie na swoich miejscach z kolejności bazowej. Dzięki temu:

- bez nauki wynik jest identyczny z dzisiejszym (zimny start bez zmiany zachowania),
- nowy produkt pojawia się tam, gdzie pojawiłby się dotąd (alfabetycznie między sąsiadami), zamiast skakać na początek lub koniec,
- wynik jest deterministyczny i łatwy do przetestowania.

Odrzucona alternatywa: niewyuczone na końcu — nowy produkt lądowałby za całą kategorią, a pierwsze „Mrożonki” za „Chemią”, co psuje dotychczasową intuicję.

### D5. Przypięcia bez zmian: kolejność wyuczona jako nowa baza

- Kategorie: `arrange(learned(list(Category), scores), pins)` — przypięcie dalej jest numerem miejsca w pełnej kolejności, a nieprzypięte wypełniają resztę w kolejności wyuczonej.
- Produkty: `arrange_anchored(learned(sorted(names), scores), pins)` — kotwice z #34 zostały zaprojektowane tak, by przetrwać zmianę bazy (przypięty produkt zostaje za swoim sąsiadem).
- Przypinanie (`PUT …/order`) wylicza miejsce upuszczenia na tej samej kolejności, którą widzi użytkownik (wyuczonej), więc „między A i B” znaczy to samo co na ekranie.

### D6. Liczenie w locie zamiast nowej tabeli

Kolejność liczymy przy każdym odczycie z historii, bez migracji:

- Koszt: jedno zapytanie (drugie tylko przy zimnym starcie) o pozycje z najwyżej 10 przejść — typowo kilkadziesiąt do kilkuset wierszy, wybieranych po indeksach `shopping_trips(household_id, finished_at)` i `purchased_items(trip_id)`; wyliczenie w Pythonie jest liniowe. `GET /api/list` (i odpowiedzi mutacji listy) liczą naukę raz i używają jej dla kategorii i produktów.
- Historia jest niezmienna, a przybywa jej tylko przy „Zakończ zakupy”, więc wynik jest deterministyczny i zawsze aktualny — bez unieważniania pamięci podręcznej, bez rozjazdu przy usunięciu konta czy zmianie gospodarstwa.
- Odrzucona alternatywa: tabela wyników per użytkownik aktualizowana przy zakończeniu zakupów — szybszy odczyt, ale migracja, denormalizacja, przeliczanie dla wszystkich członków i trudniejsza zmiana heurystyki (trzeba by przeliczać zapisane wyniki). Gdy odczyt okaże się za drogi, można dodać taką pamięć podręczną bez zmiany API.

### D7. Stabilność w trakcie zakupów

Uczymy się tylko z zakończonych zakupów, więc odhaczanie nie przestawia listy w trakcie zakupów. Po „Zakończ zakupy” lista i tak jest odświeżana sygnałem `list_changed` dla całego gospodarstwa, więc nowa kolejność dociera bez dodatkowych zdarzeń.

## Risks / Trade-offs

- [Odhaczanie hurtem (w domu, przez czat)] → przejście bez sensownej kolejności; mediana z 10 przejść tłumi pojedyncze takie przejścia, a stałe łatwo zmienić.
- [Kilka sklepów o różnym układzie] → kolejność to „mediana” sklepów; per sklep — poza zakresem, przypięcia pozwalają poprawić to, co ważne.
- [Zakończenie zakupów obejmujące kilka wizyt w sklepie] → traktowane jak jedno przejście; względne miejsca nadal oddają kolejność w obrębie wizyt.
- [Koszt odczytu przy każdym pobraniu listy] → ograniczony oknem 10 przejść i indeksami; w razie potrzeby pamięć podręczna (D6).
- [Kolejność zmienia się po zakończeniu zakupów bez akcji użytkownika] → to cel funkcji; zmiana jest stopniowa (mediana), a przypięcia zawsze wygrywają.
