## ADDED Requirements

### Requirement: Pasek nawigacji
Główny widok MUST mieć pasek nawigacji złożony wyłącznie z trzech elementów: „Kupto”, tytułu czatu i ikony profilu. „Kupto” MUST prowadzić do głównego widoku. Tytułem czatu MUST być nazwa gospodarstwa użytkownika. Ikona profilu MUST prowadzić do strony profilu, MUST mieć dostępną etykietę „Profil” i cel dotyku co najmniej 44×44 px.

#### Scenario: Elementy paska
- **WHEN** zalogowany członek gospodarstwa „Dom” otwiera główny widok
- **THEN** pasek zawiera tylko „Kupto”, przycisk z tytułem „Dom” i link „Profil”

#### Scenario: Powrót do głównego widoku
- **WHEN** użytkownik stuka „Kupto”
- **THEN** widzi główny widok z czatem i listą

### Requirement: Pasek na wąskim ekranie
Pasek nawigacji MUST mieścić się w jednym wierszu przy szerokości ekranu od 320 do 430 px bez przewijania strony w poziomie. Zbyt długi tytuł czatu MUST zostać skrócony, a nie zawinięty. Pasek MUST omijać notch (górne wcięcie safe-area).

#### Scenario: Wąski telefon i długa nazwa
- **WHEN** gospodarstwo ma nazwę dłuższą niż szerokość paska, a ekran ma 320 px szerokości
- **THEN** pasek zajmuje jeden wiersz, tytuł jest skrócony wielokropkiem, a strony nie da się przewinąć w bok

### Requirement: Opcje czatu
Stuknięcie tytułu czatu MUST otworzyć opcje czatu. Opcje czatu MUST pozwalać wyczyścić historię rozmowy z asystentem po potwierdzeniu i MUST zawierać link do strony gospodarstwa. Opcje MUST dać się zamknąć przyciskiem „Zamknij” i klawiszem Escape.

#### Scenario: Wyczyszczenie historii z opcji czatu
- **WHEN** użytkownik otwiera opcje czatu, wybiera „Wyczyść historię czatu” i potwierdza
- **THEN** historia rozmowy jest usuwana, a czat pokazuje pusty wątek

#### Scenario: Rezygnacja z wyczyszczenia
- **WHEN** użytkownik wybiera „Wyczyść historię czatu”, ale nie potwierdza
- **THEN** historia rozmowy pozostaje bez zmian

#### Scenario: Zamknięcie opcji
- **WHEN** opcje czatu są otwarte, a użytkownik naciska Escape
- **THEN** opcje się zamykają, a fokus wraca na tytuł czatu

### Requirement: Strona profilu
Strona profilu (`/profile`) MUST pokazywać login użytkownika i nazwę gospodarstwa oraz zawierać linki do: strony gospodarstwa (domownicy, preferencje, ustawienia powiadomień), historii zakupów, przepisów i planu obiadów, a także przycisk „Wyloguj” oraz link powrotu do głównego widoku. Wylogowanie z profilu MUST działać tak samo jak dotąd z paska.

#### Scenario: Zawartość profilu
- **WHEN** użytkownik „ala” z gospodarstwa „Dom” otwiera profil
- **THEN** widzi „ala”, „Dom” i linki Gospodarstwo, Historia zakupów, Przepisy, Plan obiadów oraz przycisk „Wyloguj”

#### Scenario: Wylogowanie z profilu
- **WHEN** użytkownik stuka „Wyloguj” na profilu
- **THEN** sesja zostaje zakończona, a użytkownik widzi ekran logowania
