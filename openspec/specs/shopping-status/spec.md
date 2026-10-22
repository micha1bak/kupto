# shopping-status Specification

## Purpose
Status członka gospodarstwa „robię zakupy”: pozwala domownikom zobaczyć, kto jest teraz w sklepie i od kiedy, i jest punktem odczytu dla powiadomień o zakupach.

## Requirements

### Requirement: Włączenie statusu zakupów
Członek gospodarstwa MUST móc oznaczyć, że idzie na zakupy. Status MUST zapamiętać chwilę rozpoczęcia. Ponowne włączenie aktywnego statusu MUST NOT zmieniać chwili rozpoczęcia.

#### Scenario: Idę na zakupy
- **WHEN** ala wybiera „Idę na zakupy”
- **THEN** ala ma aktywny status zakupów z chwilą rozpoczęcia równą chwili włączenia

#### Scenario: Ponowne włączenie w trakcie
- **WHEN** ala ma aktywny status od 14:00 i o 14:30 ponownie wybiera „Idę na zakupy”
- **THEN** status ali nadal zaczyna się o 14:00

### Requirement: Wyłączenie statusu zakupów
Członek MUST móc wyłączyć swój status zakupów. Zakończenie zakupów (przeniesienie kupionych pozycji do historii) MUST wyłączyć status członka, który je wykonał, także gdy nie było kupionych pozycji, i MUST NOT zmieniać statusu pozostałych członków. Opuszczenie gospodarstwa lub usunięcie z niego MUST wyłączyć status.

#### Scenario: Kończę
- **WHEN** ala ma aktywny status i wybiera „Kończę”
- **THEN** ala nie ma aktywnego statusu, a pozycje listy się nie zmieniają

#### Scenario: Zakończenie zakupów zdejmuje status kończącego
- **WHEN** ala i ola mają aktywny status, a ala kończy zakupy
- **THEN** ala nie ma aktywnego statusu, a ola nadal ma

#### Scenario: Odejście z gospodarstwa
- **WHEN** ala ma aktywny status i opuszcza gospodarstwo
- **THEN** ala nie ma aktywnego statusu

### Requirement: Wygasanie statusu zakupów
Status zakupów MUST przestać być aktywny po 3 godzinach od chwili rozpoczęcia bez żadnego działania użytkownika. Po wygaśnięciu członek MUST móc włączyć status ponownie z nową chwilą rozpoczęcia.

#### Scenario: Status wygasa
- **WHEN** ala włączyła status 3 godziny i 1 minutę temu i od tego czasu go nie zmieniała
- **THEN** ala nie jest pokazywana jako robiąca zakupy

#### Scenario: Ponowne włączenie po wygaśnięciu
- **WHEN** status ali wygasł, a ala znów wybiera „Idę na zakupy”
- **THEN** ala ma aktywny status z nową chwilą rozpoczęcia

### Requirement: Widoczność statusu zakupów dla domowników
Każdy członek gospodarstwa MUST widzieć przy liście zakupów, którzy członkowie jego gospodarstwa mają teraz aktywny status zakupów i od kiedy. Status MUST być widoczny wyłącznie dla członków tego samego gospodarstwa i MUST pojawiać się u nich tak samo szybko jak zmiany listy.

#### Scenario: Ania robi zakupy
- **WHEN** ania włącza status zakupów
- **THEN** bartek z tego samego gospodarstwa widzi przy liście „ania robi zakupy” z godziną rozpoczęcia

#### Scenario: Inne gospodarstwo nie widzi statusu
- **WHEN** ania włącza status zakupów
- **THEN** członkowie innych gospodarstw nie widzą jej statusu
