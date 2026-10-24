# Design

## Context

Zasada 7 mówiła „Po każdej zmianie krótko wymień, co zostało zrobione”, ale nie zakazywała pytań zamykających, a zasada 1 kazała po odmowie „zaproponować pomoc w zakupach” — model (`openai/gpt-oss-120b`) uogólnia to na kończenie wielu odpowiedzi ofertą lub pytaniem. Instrukcja systemowa trafia do każdego wywołania, więc zmiana nie może jej wydłużać.

## Goals / Non-Goals

**Goals:**
- Po akcji: krótka informacja, co zrobiono, bez pytania zamykającego.
- Pytania potwierdzające (zasady 4, 4a–4e, 6) i dopytywanie przy niejasności bez zmian.
- Instrukcja dłuższa najwyżej o jedno zdanie.

**Non-Goals:**
- Filtrowanie odpowiedzi po stronie serwera (np. obcinanie końcowego pytania) — zawodne i psułoby pytania potwierdzające.
- Zmiana treści wyników narzędzi.

## Decisions

### D1. Jedna zasada stylu z przykładem pozytywnym i negatywnym

Zasada 7 łączy zwięzłość (dotąd w zasadzie 8), wzór odpowiedzi („Dodałem mleko 2 l i chleb.”) i jeden przykład zakazanego pytania. Wyjątek jest sformułowany ogólnie („potwierdzenie wymagane przez te zasady albo gdy bez odpowiedzi nie da się wykonać prośby”) zamiast wyliczać 4, 4a–4e i 6 — krócej, a każda z tych zasad i tak mówi „zapytaj”.

Rozważone: osobny akapit „Styl odpowiedzi” na końcu — dłuższy i dublowałby zasadę 7.

### D2. Usunięcie zachęty do ofert

Odmowa w zasadzie 1 kończy się stwierdzeniem („pisząc, że pomagasz w zakupach”) zamiast propozycji pomocy — wymaganie „wrócić do tematu zakupów” jest spełnione bez pytania. Przypomnienie listy przy starcie zakupów (zasada 9) zostaje — to informacja, nie pytanie zamykające. Zwięźlejsze zasady 2, 6 i 9 pokrywają większość nowej treści zasady 7; zasada 8 zostaje jednoznaczna co do języka odpowiedzi.

### D3. Ewaluacje

Pomocnik `assert_no_closing_question`: odpowiedź nie kończy się „?” (po zdjęciu znaczników markdown, nawiasów i cudzysłowów) i nie zawiera typowych formuł („coś jeszcze”, „w czym jeszcze” …); bez „mogę pomóc”, które daje fałszywe trafienia. Dopisany do istniejących scenariuszy akcji zamiast nowych rozmów — bez dodatkowych wywołań modelu. W scenariuszach wymagających zgody sprawdzany jest stan (nic nie dodane ani zapisane przed potwierdzeniem), a nie znak zapytania — potwierdzenie może być sformułowane bez niego.
