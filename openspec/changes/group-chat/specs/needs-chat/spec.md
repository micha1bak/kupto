## REMOVED Requirements

### Requirement: Prywatna historia rozmowy
**Reason**: Czat asystenta staje się czatem grupowym gospodarstwa (#78) — zastępuje go wymaganie „Czat grupowy gospodarstwa”.
**Migration**: Dotychczasowe prywatne historie zostają w bazie jako archiwum (`chat_messages.private = true`), niewidoczne w wątku gospodarstwa i w kontekście modelu; cofnięcie migracji 0012 przywraca prywatne wątki.

## ADDED Requirements

### Requirement: Czat grupowy gospodarstwa
Każde gospodarstwo MUST mieć jeden wspólny, trwały wątek czatu, w którym wszyscy jego członkowie widzą wiadomości pozostałych członków i odpowiedzi asystenta. Każda wiadomość MUST mieć czas utworzenia; wiadomość członka MUST wskazywać autora (imię, a dla konta bez imienia login), a odpowiedź asystenta MUST być oznaczona jako odpowiedź asystenta. Członek MUST NOT widzieć wątku innego gospodarstwa ani zarchiwizowanych prywatnych rozmów sprzed czatu grupowego.

#### Scenario: Wiadomości domowników w jednym wątku
- **WHEN** ala pisze „kup mleko”, a potem ola pobiera wątek czatu
- **THEN** ola widzi wiadomość ali z jej imieniem i godziną oraz odpowiedź oznaczoną jako odpowiedź asystenta

#### Scenario: Inne gospodarstwo
- **WHEN** członek innego gospodarstwa pobiera wątek czatu
- **THEN** nie widzi wiadomości z gospodarstwa ali

#### Scenario: Archiwum prywatnych rozmów
- **WHEN** po wdrożeniu czatu grupowego członek pobiera wątek
- **THEN** nie widzi wiadomości ze swojej ani cudzej prywatnej rozmowy sprzed zmiany, a model ich nie dostaje

### Requirement: Asystent w czacie grupowym
Asystent MUST odpowiadać na każdą wiadomość członka, uwzględniając ostatnie wiadomości wątku z imionami autorów oraz aktualny stan listy. Zmiany listy MUST zapisywać się jako zmiany autora wiadomości, na którą asystent odpowiada.

#### Scenario: Kontekst rozmowy grupy
- **WHEN** ala napisała „robię naleśniki w sobotę”, a ola pisze „dodaj do tego mleko”
- **THEN** model dostaje obie wiadomości z imionami autorów, a mleko trafia na listę jako zapotrzebowanie oli

### Requirement: Wiadomości czatu na żywo
Zapisanie wiadomości członka i odpowiedzi asystenta MUST powodować sygnał `chat_changed` w strumieniu zmian gospodarstwa, tak by pozostali członkowie z otwartą aplikacją zobaczyli nową wiadomość bez odświeżania strony. Sygnał MUST NOT zawierać treści wiadomości.

#### Scenario: Nowa wiadomość u domownika
- **WHEN** ola ma otwarty czat, a ala wysyła wiadomość
- **THEN** strumień oli dostaje `chat_changed`, a jej czat pokazuje wiadomość ali, a po zakończeniu odpowiedzi także odpowiedź asystenta

#### Scenario: Inne gospodarstwo bez sygnału
- **WHEN** ala wysyła wiadomość
- **THEN** strumienie członków innych gospodarstw nie dostają `chat_changed`

### Requirement: Potwierdzenia w czacie grupowym
Akcję wymagającą potwierdzenia (zakończenie zakupów, propozycja produktów, składników lub planu obiadów) MUST móc potwierdzić tylko członek, który o nią poprosił. Oczekujące potwierdzenie zakończenia zakupów MUST być przypisane do autora prośby i MUST wygasać przy jego następnej wiadomości; wiadomości innych członków MUST NOT go potwierdzać ani unieważniać.

#### Scenario: Potwierdzenie od innego domownika
- **WHEN** asystent zapytał alę, czy zakończyć zakupy, a ola odpowiada „tak”
- **THEN** zakupy nie zostają zakończone, a prośba ali nadal czeka na jej odpowiedź

#### Scenario: Potwierdzenie od autora po wiadomości innego domownika
- **WHEN** asystent zapytał alę, czy zakończyć zakupy, ola napisała „kup chleb”, a potem ala odpowiada „tak”
- **THEN** zakupy zostają zakończone

### Requirement: Ukrycie historii czatu u siebie
Członek MUST móc ukryć u siebie dotychczasowe wiadomości wątku gospodarstwa. Ukrycie MUST NOT usuwać wiadomości ani zmieniać tego, co widzą pozostali członkowie i co dostaje model; nowe wiadomości MUST być widoczne normalnie.

#### Scenario: Ukrycie u siebie
- **WHEN** ala ukrywa historię czatu
- **THEN** wątek ali jest pusty, wątek oli zawiera wszystkie wiadomości, a lista zakupów się nie zmienia

#### Scenario: Nowe wiadomości po ukryciu
- **WHEN** ala ukryła historię, a potem ola wysyła wiadomość
- **THEN** ala widzi wiadomość oli i odpowiedź asystenta
