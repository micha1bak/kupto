## MODIFIED Requirements

### Requirement: Wysyłanie wiadomości i strumieniowana odpowiedź
Członek gospodarstwa MUST móc wysłać do asystenta wiadomość tekstową (1–8000 znaków, by zmieścił się wklejony przepis). Odpowiedź asystenta MUST być przesyłana przyrostowo w trakcie generowania, a jej zakończenie MUST być jednoznacznie sygnalizowane.

#### Scenario: Zwykła wiadomość
- **WHEN** członek wysyła „Skończył się chleb”
- **THEN** klient otrzymuje odpowiedź asystenta w kolejnych fragmentach, a na końcu sygnał zakończenia

#### Scenario: Wklejony długi przepis
- **WHEN** członek wysyła przepis z opisem przygotowania liczący 5000 znaków
- **THEN** system przyjmuje wiadomość i przekazuje ją asystentowi

#### Scenario: Zbyt długa wiadomość
- **WHEN** członek wysyła wiadomość dłuższą niż 8000 znaków
- **THEN** system odrzuca ją z kodem 422 bez wywoływania modelu

## ADDED Requirements

### Requirement: Lista zakupów z przepisu
Gdy członek wkleja przepis, asystent MUST wypisać jego składniki z ilościami, MUST zapytać, których brakuje, i MUST NOT zmieniać listy, dopóki członek nie odpowie. Asystent SHOULD pominąć oczywiste podstawy kuchni (woda, sól, pieprz) i MUST wspomnieć, że je pominął. Po odpowiedzi asystent MUST dodać jako zapotrzebowania autora wyłącznie brakujące składniki, każdy z notatką „na: <danie>”, z ilością i jednostką, gdy przepis podaje je w jednostkach listy.

#### Scenario: Wklejony przepis
- **WHEN** członek wkleja przepis na naleśniki (mąka, mleko, jajka, woda, szczypta soli, olej)
- **THEN** asystent wymienia mąkę, mleko, jajka i olej z ilościami, wspomina o pominięciu wody i soli, pyta, czego brakuje, a lista pozostaje bez zmian

#### Scenario: Członek wskazuje brakujące składniki
- **WHEN** po propozycji składników naleśników członek odpowiada „brakuje mi tylko mleka i jajek”
- **THEN** na liście pojawiają się zapotrzebowania członka na mleko i jajka z notatką „na: naleśniki”, a mąki i oleju nie ma

#### Scenario: Członek wskazuje, co ma
- **WHEN** po propozycji składników członek odpowiada „mąkę i olej mam, resztę dodaj”
- **THEN** asystent dodaje pozostałe zaproponowane składniki z notatką „na: <danie>”, bez mąki i oleju
