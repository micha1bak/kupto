# Design

## Context

Zasada 7 mówiła „Po każdej zmianie krótko wymień, co zostało zrobione”, ale nie zakazywała pytań zamykających, a zasada 1 kazała po odmowie „zaproponować pomoc w zakupach” — model (`openai/gpt-oss-120b`) uogólnia to na kończenie wielu odpowiedzi ofertą lub pytaniem. Instrukcja systemowa trafia do każdego wywołania, więc zmiana nie może jej wydłużać.

## Goals / Non-Goals

**Goals:**
- Po akcji: krótka informacja, co zrobiono, bez pytania zamykającego.
- Pytania potwierdzające (zasady 4, 4a–4e, 6) i dopytywanie przy niejasności bez zmian.
- Instrukcja nie dłuższa niż dotąd.

**Non-Goals:**
- Filtrowanie odpowiedzi po stronie serwera (np. obcinanie końcowego pytania) — zawodne i psułoby pytania potwierdzające.
- Zmiana treści wyników narzędzi.

## Decisions

### D1. Jedna zasada stylu z przykładem pozytywnym i negatywnym

Zasada 7 łączy zwięzłość (dotąd w zasadzie 8), wzór odpowiedzi („Dodałem mleko 2 l i chleb.”) i jeden przykład zakazanego pytania. Wyjątek jest sformułowany ogólnie („potwierdzenie wymagane przez te zasady albo niejasna prośba”) zamiast wyliczać 4, 4a–4e i 6 — krócej, a każda z tych zasad i tak mówi „zapytaj”.

Rozważone: osobny akapit „Styl odpowiedzi” na końcu — dłuższy i dublowałby zasadę 7.

### D2. Usunięcie zachęt do pytań

Odmowa w zasadzie 1 kończy się stwierdzeniem („pisząc, że pomagasz w zakupach”) zamiast propozycji pomocy — wymaganie „wrócić do tematu zakupów” jest spełnione bez pytania. Z zasady 9 znika „możesz krótko przypomnieć, co jest do kupienia” (opcjonalna dopowiedź, która zachęcała do dłuższych odpowiedzi). Zaoszczędzone znaki (także zwięźlejsze zasady 2, 6, 8) pokrywają nową treść zasady 7.

### D3. Ewaluacje

Pomocnik `assert_no_closing_question`: odpowiedź nie kończy się „?” (po zdjęciu znaczników markdown) i nie zawiera typowych formuł („coś jeszcze”, „mogę pomóc” …). Dopisany do istniejących scenariuszy akcji zamiast nowych rozmów — bez dodatkowych wywołań modelu. W scenariuszach wymagających zgody dopisane `"?" in reply`, by zakaz nie zjadł pytań potwierdzających.
