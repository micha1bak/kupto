# Proposal

## Why

Asystent kończy odpowiedzi pytaniami w stylu „Czy potrzebujesz czegoś jeszcze?” albo ofertą dalszej pomocy, także po zwykłym dodaniu produktu czy odhaczeniu kupionego. To wydłuża rozmowę, męczy przy częstym użyciu i rozmywa pytania, które naprawdę wymagają odpowiedzi (potwierdzenie propozycji, zakończenia zakupów, planu obiadów). #79.

## What Changes

- Instrukcja systemowa czatu: zasada 7 mówi wprost, że po zmianie asystent krótko pisze, co zrobił (np. „Dodałem mleko 2 l i chleb.”), i nie kończy pytaniem zamykającym; pytania zostają tylko tam, gdzie zasady wymagają potwierdzenia (4, 4a–4e, 6), albo gdy bez odpowiedzi nie da się wykonać prośby.
- Usunięte sformułowanie zachęcające do ofert: odmowa w zasadzie 1 nie „proponuje pomocy w zakupach”, tylko mówi, że asystent pomaga w zakupach. Krótkie przypomnienie, co jest do kupienia, przy starcie zakupów (zasada 9) zostaje — to informacja, nie pytanie.
- Prompt rośnie minimalnie: zasady 2, 6 i 9 zwięźlej, „zwięźle” przeniesione z zasady 8 do 7 (instrukcja łącznie dłuższa o ok. 80 znaków).
- Ewaluacje (`-m llm`): brak pytania zamykającego po dodaniu produktów, potwierdzonej propozycji, odhaczeniu, potwierdzonym zakończeniu zakupów i zapamiętaniu preferencji; pytanie zostaje przy propozycji ogólnej potrzeby, prośbie o zakończenie zakupów i planie obiadów.
- Poza zakresem: zmiany w narzędziach, frontendzie i API.

## Capabilities

### New Capabilities

Brak.

### Modified Capabilities

- `needs-chat`: nowe wymaganie „Odpowiedź po wykonanej akcji”.

## Impact

- **Backend**: `chat/prompt.py` (zasady 1, 2, 6–9), `tests/test_chat_prompt.py`, `evals/test_assistant_behaviour.py`.
- **Koszt LLM**: ok. 20 tokenów więcej w instrukcji systemowej; krótsze odpowiedzi (bez pytań zamykających) to mniej tokenów wyjściowych.
