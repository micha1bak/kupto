# Spec Delta

## Purpose

Grupuje użytkowników w gospodarstwa domowe, które współdzielą jedną listę zakupów i do których zgłaszane są zapotrzebowania w czacie.

## ADDED Requirements

### Requirement: Utworzenie gospodarstwa
System MUST umożliwiać zalogowanemu użytkownikowi, który nie należy do żadnego gospodarstwa, utworzenie gospodarstwa o nazwie (1–100 znaków). Twórca MUST zostać jego właścicielem i jedynym członkiem, a gospodarstwo MUST otrzymać pustą aktywną listę zakupów.

#### Scenario: Utworzenie pierwszego gospodarstwa
- **WHEN** użytkownik bez gospodarstwa tworzy gospodarstwo „Dom”
- **THEN** system tworzy gospodarstwo z użytkownikiem jako właścicielem i pustą listą zakupów

#### Scenario: Użytkownik już należy do gospodarstwa
- **WHEN** członek istniejącego gospodarstwa próbuje utworzyć kolejne
- **THEN** system odrzuca żądanie z kodem 409

### Requirement: Przynależność do jednego gospodarstwa
Użytkownik MUST należeć do co najwyżej jednego gospodarstwa naraz. Czat i lista zakupów MUST być niedostępne (kod 409 z informacją o braku gospodarstwa) dla użytkownika bez gospodarstwa.

#### Scenario: Czat bez gospodarstwa
- **WHEN** użytkownik bez gospodarstwa wysyła wiadomość do czatu
- **THEN** system zwraca 409 z informacją, że należy najpierw utworzyć gospodarstwo lub dołączyć do niego

### Requirement: Dodawanie członków
Właściciel gospodarstwa MUST móc dodać innego użytkownika po jego loginie. Dodanie MUST się nie udać, jeśli użytkownik nie istnieje (404) albo należy już do jakiegokolwiek gospodarstwa (409). Członkowie niebędący właścicielem MUST NOT móc dodawać członków (403).

#### Scenario: Dodanie użytkownika
- **WHEN** właściciel dodaje istniejącego użytkownika bez gospodarstwa
- **THEN** użytkownik staje się członkiem i widzi wspólną listę zakupów

#### Scenario: Nieistniejący login
- **WHEN** właściciel podaje login, który nie istnieje
- **THEN** system zwraca 404

#### Scenario: Dodawanie przez zwykłego członka
- **WHEN** członek niebędący właścicielem próbuje dodać użytkownika
- **THEN** system zwraca 403

### Requirement: Lista członków
Każdy członek gospodarstwa MUST móc pobrać listę członków z ich loginami i wskazaniem właściciela.

#### Scenario: Podgląd członków
- **WHEN** członek pobiera dane gospodarstwa
- **THEN** odpowiedź zawiera nazwę gospodarstwa i wszystkich członków z oznaczeniem właściciela

### Requirement: Usuwanie członków
Właściciel MUST móc usunąć z gospodarstwa dowolnego członka poza sobą. Usunięty użytkownik MUST natychmiast utracić dostęp do listy i czatu gospodarstwa; zgłoszone przez niego pozycje MUST pozostać na liście.

#### Scenario: Usunięcie członka
- **WHEN** właściciel usuwa członka
- **THEN** członek traci dostęp do listy, a jego wcześniej zgłoszone pozycje pozostają na liście

#### Scenario: Próba usunięcia właściciela
- **WHEN** właściciel próbuje usunąć samego siebie przez usuwanie członków
- **THEN** system zwraca 403 i wskazuje opuszczenie gospodarstwa jako właściwą operację

### Requirement: Opuszczenie gospodarstwa
Każdy członek MUST móc opuścić gospodarstwo. Gdy opuszcza je właściciel, a są inni członkowie, własność MUST przejść na członka o najdłuższym stażu. Gdy odchodzi ostatni członek, gospodarstwo wraz z listą i historią czatu MUST zostać usunięte.

#### Scenario: Członek opuszcza gospodarstwo
- **WHEN** zwykły członek opuszcza gospodarstwo
- **THEN** przestaje być członkiem, a gospodarstwo działa dalej bez zmian

#### Scenario: Właściciel opuszcza gospodarstwo
- **WHEN** właściciel opuszcza gospodarstwo z innymi członkami
- **THEN** właścicielem zostaje członek o najdłuższym stażu

#### Scenario: Odchodzi ostatni członek
- **WHEN** jedyny członek opuszcza gospodarstwo
- **THEN** gospodarstwo, jego lista zakupów i historia czatu zostają usunięte
