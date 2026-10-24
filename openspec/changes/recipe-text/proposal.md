# Proposal

## Why

Gotowanie z przepisu to typowy powód zakupów: ktoś znajduje przepis i musi przepisać składniki na listę, sprawdzając po drodze, co już jest w domu. Asystent potrafi to zrobić za niego (#42, epik #41) — ale dziś wiadomość czatu ma limit 2000 znaków, w który przepis z opisem przygotowania często się nie mieści.

## What Changes

- Asystent rozpoznaje wklejony przepis: wypisuje jego składniki z ilościami (pomijając oczywiste podstawy kuchni — wodę, sól i pieprz — z krótką wzmianką, że je pominął), pyta, czego z tego brakuje, i **nie zmienia listy** do odpowiedzi.
- Po odpowiedzi (np. „brakuje mi tylko jajek i mleka”, „mam mąkę, resztę dodaj”, „dodaj wszystko”) dodaje wyłącznie brakujące składniki jako zapotrzebowania autora, z notatką „na: <danie>”.
- Ilości z przepisu przenoszone na jednostki listy (szt, kg, g, l, ml, opak); miary kuchenne bez odpowiednika (łyżka, szklanka) trafiają do notatki zamiast ilości.
- Limit długości wiadomości czatu podniesiony z 2000 do 8000 znaków (backend i frontend), żeby zmieścił się przepis z opisem.
- Bez nowego narzędzia i bez stanu po stronie serwera — przepływ „propozycja → potwierdzenie” jak przy ogólnych potrzebach (zasada 4). Bez migracji.
- Poza zakresem: przepis z linku (#43, osobna zmiana `recipe-link`), zapisywanie przepisów i planowanie posiłków (#44–#47).

## Capabilities

### New Capabilities

_(brak)_

### Modified Capabilities

- `needs-chat`: zmienione wymaganie „Wysyłanie wiadomości i strumieniowana odpowiedź” (limit 8000 znaków); nowe wymaganie „Lista zakupów z przepisu”.

## Impact

- **Backend**: zasada w `chat/prompt.py`, stała `MAX_MESSAGE_LENGTH` w `chat/router.py`. Bez migracji i nowych zależności.
- **Frontend**: `MAX_LENGTH` w `chat/ChatView.tsx`, podpowiedź w pustym czacie.
- **Koszt**: dłuższe wiadomości to więcej tokenów wejściowych w kolejnych turach (przepis zostaje w historii, którą model dostaje — do `chat_history_limit` wiadomości). Limit wiadomości na godzinę bez zmian.
