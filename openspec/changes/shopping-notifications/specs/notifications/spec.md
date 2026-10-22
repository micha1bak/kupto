## ADDED Requirements

### Requirement: Powiadomienie o rozpoczęciu zakupów
Gdy członek gospodarstwa włącza status zakupów, który nie był aktywny (przyciskiem lub przez czat), pozostali członkowie gospodarstwa MUST dostać powiadomienie „{login} idzie na zakupy” z zachętą do dopisania potrzebnych produktów. Ponowne włączenie aktywnego statusu MUST NOT wysyłać powiadomienia. Autor MUST NOT dostać własnego powiadomienia.

#### Scenario: Rozpoczęcie zakupów
- **WHEN** ala włącza status zakupów
- **THEN** ola i ewa z jej gospodarstwa dostają „ala idzie na zakupy”, a ala i członkowie innych gospodarstw nie

#### Scenario: Rozpoczęcie przez czat
- **WHEN** ala pisze w czacie, że idzie do sklepu, a asystent włącza jej status
- **THEN** pozostali domownicy dostają to samo powiadomienie

#### Scenario: Status już aktywny
- **WHEN** ala z aktywnym statusem ponownie włącza status
- **THEN** nikt nie dostaje powiadomienia

### Requirement: Powiadomienie o dopisaniu w trakcie zakupów
Gdy ktoś dodaje zapotrzebowanie (ręcznie lub przez czat), a inni członkowie gospodarstwa mają aktywny status zakupów, każdy z tych kupujących (poza autorem zmiany) MUST dostać powiadomienie z nazwami niekupionych produktów dopisanych przez innych w trakcie jego zakupów w ostatnich minutach. Kolejne dopisania MUST aktualizować jedno powiadomienie na urządzeniu zamiast dokładać nowe. Gdy nikt inny nie robi zakupów, powiadomienie MUST NOT być wysyłane. Powiadomienie MUST mieć wysoką pilność.

#### Scenario: Dopisanie, gdy ola jest w sklepie
- **WHEN** ola ma aktywny status, a ala dodaje mleko
- **THEN** ola dostaje powiadomienie „Dopisano w trakcie zakupów” z treścią „mleko”, a ala i ewa (bez statusu) nie dostają nic

#### Scenario: Kilka dopisań
- **WHEN** ola ma aktywny status, a ala i ewa w ciągu kilku minut dodają mleko, chleb i masło
- **THEN** ola widzi jedno powiadomienie z nazwami wszystkich trzech produktów

#### Scenario: Nikt nie robi zakupów
- **WHEN** nikt w gospodarstwie nie ma aktywnego statusu, a ala dodaje mleko
- **THEN** nikt nie dostaje powiadomienia

#### Scenario: Kupujący dopisuje sam
- **WHEN** ola z aktywnym statusem sama dodaje kawę
- **THEN** ola nie dostaje powiadomienia

#### Scenario: Produkty sprzed zakupów
- **WHEN** ala dodała jajka, zanim ola zaczęła zakupy, a potem ewa dodaje chleb
- **THEN** powiadomienie oli wymienia tylko chleb

#### Scenario: Inne gospodarstwo
- **WHEN** w innym gospodarstwie ktoś robi zakupy, a ala dodaje mleko
- **THEN** nikt nie dostaje powiadomienia

### Requirement: Powiadomienie o zakończeniu zakupów
Po zakończeniu zakupów, które przeniosło kupione pozycje do historii, pozostali członkowie gospodarstwa MUST dostać powiadomienie „{login}: zakupy zakończone” z listą pozycji, które zostały na liście niekupione, albo z informacją, że wszystko kupiono. Zakończenie bez kupionych pozycji MUST NOT wysyłać powiadomienia.

#### Scenario: Braki
- **WHEN** ala kończy zakupy z kupionym mlekiem, a chleb i masło zostały niekupione
- **THEN** ola i ewa dostają „ala: zakupy zakończone” z treścią „Nie było: chleb, masło.”

#### Scenario: Wszystko kupione
- **WHEN** ala kończy zakupy, a na liście nie zostało nic niekupionego
- **THEN** pozostali domownicy dostają „ala: zakupy zakończone” z treścią „Wszystko kupione.”

#### Scenario: Zakończenie przez czat
- **WHEN** ala potwierdza w czacie zakończenie zakupów
- **THEN** pozostali domownicy dostają to samo powiadomienie

#### Scenario: Nic nie kupiono
- **WHEN** ala kończy zakupy bez kupionych pozycji
- **THEN** nikt nie dostaje powiadomienia

### Requirement: Treść powiadomień o zakupach
Treść powiadomień o zakupach MUST być po polsku, krótka i zawierać tylko loginy i nazwy produktów z listy gospodarstwa. Lista nazw MUST obejmować najwyżej 5 produktów, a pozostałe MUST być podsumowane liczbą („i 3 inne”); zbyt długie nazwy MUST być przycięte.

#### Scenario: Wiele produktów
- **WHEN** powiadomienie dotyczy 8 produktów
- **THEN** treść wymienia 5 z nich i kończy się „i 3 inne”
