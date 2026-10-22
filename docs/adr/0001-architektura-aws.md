# ADR 0001: Architektura produkcyjna Kupto na AWS

- **Status:** zaakceptowana (#58); zaktualizowana 2026-10-22 po rozpoznaniu nowego interfejsu AWS
  z projektami (region, backupy dysku, dostęp z CLI)
- **Data:** 2026-10-22
- **Issue:** #17 (epik #16)

## Kontekst

Kupto (FastAPI + React SPA + PostgreSQL, trzy kontenery w `docker-compose.yml`) ma działać
produkcyjnie na AWS. Od wyłączenia VPS aplikacja nie jest nigdzie wdrożona.

Założenia i ograniczenia ustalone z właścicielem:

- **Skala:** jedno gospodarstwo domowe, kilka osób, ruch pomijalny. Dostępność „domowa” —
  kilka minut przerwy przy wdrożeniu lub awarii jest akceptowalne.
- **Budżet:** jak najbliżej zera. Konto AWS założone po 15.07.2025, czyli na nowym
  **Free plan**: $100 kredytu na start + do $100 za wykonanie zadań startowych, ważne do
  6 miesięcy od założenia konta lub do wyczerpania kredytów.
- **Konto w nowym interfejsie AWS (projekty)** — opis niżej; wyznacza region i sposób dostępu.
- **Domena:** właściciel ma domenę, DNS zostaje u obecnego dostawcy (rekord A na adres
  serwera).
- **IaC:** Terraform (zgodny z OpenTofu).
- **Wymagania techniczne aplikacji:**
  - długie połączenia SSE (czat dziś, lista na żywo w #26),
  - Postgres z `LISTEN/NOTIFY` (planowane rozgłaszanie zmian listy w #26),
  - migracje Alembic przy starcie backendu,
  - HTTPS z `COOKIE_SECURE=true`.

### Nowy interfejs AWS: projekty zamiast konta z użytkownikami IAM

Konto zostało założone przez „Sign up for AWS (new)” — nowy interfejs, który AWS udostępnia
części nowych klientów. Różnice istotne dla tej decyzji:

- **Projekt = osobne konto AWS.** Zasoby Kupto żyją w projekcie `kupto` (AWS Settings,
  <https://settings.aws.com> → Project → Create project). Projekty właściciela tworzą
  organizację zarządzaną przez AWS; nie konfigurujemy jej sami.
- **Region jest przydzielany, nie wybierany.** AWS przypisuje projektowi region według kraju
  z adresu kontaktowego: dla Polski **Europe (Stockholm), `eu-north-1`**. Zasoby regionalne
  powstają tylko tam; inny region wymaga przejścia na tryb zaawansowany („Activate advanced
  AWS features”), czego nie robimy. Region projektu warto potwierdzić w AWS Settings →
  Project → Overview → Additional Info przed utworzeniem zasobów.
- **Brak użytkowników IAM z dostępem do konsoli i brak IAM Identity Center / Organizations.**
  Dostęp człowieka i narzędzi z terminala to `aws login --profile kupto` z wyborem sesji
  projektu `kupto` w przeglądarce; poświadczenia są krótkotrwałe, odnawiane przez 12 godzin,
  a po 90 dniach wymagają ponownej zgody w przeglądarce. Bez długożyjących kluczy.
- **Ograniczona lista usług.** W Free Tier projektów dostępne są m.in. EC2, EBS, VPC, S3, IAM
  (role dla usług), STS, Systems Manager, AWS Backup, Budgets, Secrets Manager. **Nie ma** m.in.
  Data Lifecycle Manager, App Runner, IAM Identity Center ani Organizations.

### Free plan to nie darmowy hosting

Na nowych kontach nie ma już 12-miesięcznego free tier z limitem 750 godzin. Zamiast niego:

- usługi (w tym EC2) zużywają kredyty; na Free plan dostępne są tylko typy instancji
  oznaczone jako free tier eligible: `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`,
  `c7i-flex.large`, `m7i-flex.large`;
- po 6 miesiącach albo po wyczerpaniu kredytów konto zostaje **zawieszone** (dostęp do
  zasobów i danych znika), a jeśli w ciągu 90 dni nie przejdzie na Paid plan — **usunięte
  razem z danymi**;
- po przejściu na Paid plan niewykorzystane kredyty przechodzą na kolejne rachunki do
  wygaśnięcia.

Wniosek: architektura musi być tania w trybie płatnym, bo po pierwszych miesiącach i tak
płacimy normalne ceny. Kredyty tylko pokrywają start.

## Rozważane opcje

Koszty miesięczne w USD, `eu-north-1`, ceny on-demand, orientacyjne (zaokrąglone; ceny EC2
z oficjalnego cennika AWS, reszta do potwierdzenia przed wdrożeniem).

| Opcja | Składniki | Koszt / mies. | SSE i `LISTEN/NOTIFY` | Utrzymanie |
|---|---|---|---|---|
| **A. EC2 + Docker Compose** | `t4g.micro` (2 vCPU ARM, 1 GiB), publiczny IPv4, EBS gp3 20 GB, backup do S3 | **~12** | tak — jeden host, bez load balancera | łatki systemu po naszej stronie |
| B. Lightsail + Docker Compose | instancja 1 GiB z IPv4 w pakiecie | ~7 (90 dni próbnych na wybrane pakiety) | tak | jak A, ale słabsza integracja z IAM |
| C. ECS Fargate (Express Mode) + RDS | Fargate 0,25 vCPU/0,5 GB, ALB, RDS `db.t4g.micro`, IPv4 | ~45–55 | SSE przez ALB tak; `LISTEN/NOTIFY` na RDS tak | najmniej administracji |
| D. App Runner + RDS | — | — | — | zamknięty dla nowych klientów od 30.04.2026 i niedostępny w projektach |
| E. Lambda + baza serverless | funkcje + Aurora Serverless / DSQL | niski przy małym ruchu | SSE wymaga przepisania na streaming Lambdy; `LISTEN/NOTIFY` niedostępne w DSQL | duża przebudowa aplikacji |

Szczegóły kosztu opcji A:

| Pozycja | Koszt / mies. |
|---|---|
| EC2 `t4g.micro` ($0,0086/h w `eu-north-1`; we Frankfurcie $0,0096/h) | ~6,3 |
| Publiczny IPv4 ($0,005/h) | ~3,7 |
| EBS gp3 20 GB | ~1,7 |
| Kopie AWS Backup + backupy w S3 | <1 |
| Transfer (do 100 GB/mies. w darmowym limicie) | 0 |
| **Razem** | **~12** |

Kredyty $100–200 pokrywają więc cały okres Free plan; potem ok. $12 miesięcznie.

### Dlaczego nie pozostałe

- **B. Lightsail** — najtańszy, ale instancja nie dostaje roli IAM, więc backupy do S3
  i wdrożenie z GitHub Actions wymagają długożyjących kluczy dostępowych albo SSH
  z kluczem w sekretach. Zostaje jako zapasowa opcja, jeśli koszt A okaże się problemem.
- **C. ECS + RDS** — 3–4 razy drożej, głównie przez stały koszt ALB i RDS. Zarządzana
  baza i brak serwera do łatania nie są warte tej różnicy przy jednym gospodarstwie.
  Naturalna ścieżka migracji, jeśli Kupto kiedyś wyjdzie poza jedno gospodarstwo:
  obrazy i konfiguracja przez zmienne środowiskowe już są do tego gotowe.
- **D. App Runner** — niedostępny dla nowych klientów i w projektach.
- **E. Serverless** — wymagałby przepisania strumieniowania i rezygnacji z `LISTEN/NOTIFY`.

## Decyzja

**Opcja A: jedna instancja EC2 `t4g.micro` w projekcie `kupto` (`eu-north-1`, Sztokholm)
z obecnym Docker Compose.**

- **Compute:** `t4g.micro` (Graviton, arm64), Amazon Linux 2023, Docker + Compose plugin,
  swap 1–2 GB na zapas pamięci. Zmiana na `t4g.small` (2 GiB) to zmiana jednej zmiennej
  w Terraformie i restart, gdyby 1 GiB nie wystarczył.
- **Sieć:** domyślne VPC, Elastic IP, security group otwarta tylko na 80/443.
  Bez otwartego SSH — dostęp administracyjny przez SSM Session Manager.
- **HTTPS:** Caddy jako dodatkowy kontener przed `web`, automatyczny certyfikat
  Let's Encrypt dla subdomeny właściciela (rekord A u obecnego dostawcy DNS). Caddy
  domyślnie nie buforuje SSE. `frontend/nginx.conf` zostaje bez zmian — na jednym hoście
  Compose resolver Dockera działa jak lokalnie.
- **Baza:** Postgres 18 w kontenerze na wolumenie EBS (jak dziś), bez publicznego portu.
- **Obrazy:** budowane w GitHub Actions dla `linux/arm64` i publikowane w GHCR
  (repo jest publiczne, więc pobieranie nie wymaga poświadczeń i nie kosztuje).
- **Sekrety:** SSM Parameter Store (SecureString, warstwa standard — bez opłat); przy
  starcie usługi skrypt na instancji generuje z nich `.env` dla Compose.
- **Wdrożenie (#21):** GitHub Actions przez OIDC (bez kluczy AWS w sekretach) przyjmuje rolę
  z uprawnieniem tylko do `ssm:SendCommand` na tę instancję; komenda wykonuje
  `docker compose pull && docker compose up -d` i sprawdza `/api/health`. Dostawca OIDC
  i rola powstają w IAM projektu; ich dostępność w projektach sprawdzamy w #18 — gdyby
  zasady projektu je blokowały, wracamy do tej decyzji przed #21.
- **Backupy (#22):** codzienny `pg_dump` do S3 (retencja przez lifecycle policy) z roli
  instancji + cotygodniowe kopie wolumenu EBS przez **AWS Backup** (plan backupu wybierający
  wolumen po tagu). Data Lifecycle Manager nie jest dostępny w projektach.
- **Terraform (#18):** stan w S3 z natywnym blokowaniem (`use_lockfile`, bez DynamoDB);
  kod w `infra/`; provider z `profile = "kupto"` i `region = "eu-north-1"` oraz
  `default_tags` z `Project = "kupto"`.
- **Dostęp lokalny:** AWS CLI v2 i `aws login --profile kupto` (sesja projektu `kupto`),
  region profilu `eu-north-1`. Terraform i inne narzędzia korzystają z tego samego profilu.

## Konsekwencje

- **Pozytywne:** najniższy koszt w trybie płatnym; zero zmian w aplikacji i w
  `docker-compose.yml` poza dodaniem Caddy; SSE i `LISTEN/NOTIFY` działają bez dodatkowych
  usług; osobny projekt izoluje Kupto od innych zasobów właściciela; prosta migracja do
  opcji C w przyszłości.
- **Negatywne:**
  - pojedynczy punkt awarii, brak automatycznego przełączania; przy awarii instancji
    odtwarzamy ją z Terraformu i backupu;
  - aktualizacje systemu i Dockera po naszej stronie (automatyczne łatki bezpieczeństwa
    `dnf-automatic`);
  - pamięć 1 GiB to niewielki zapas — do obserwacji w #23;
  - region narzucony przez projekt; zmiana regionu oznaczałaby przejście na tryb
    zaawansowany.
- **Wymagania dla kolejnych zadań:**
  - **#18:** zacząć od potwierdzenia regionu projektu i sprawdzenia, czy w IAM projektu można
    utworzyć dostawcę OIDC dla GitHub Actions oraz rolę instancji;
  - **#21:** CI musi budować obrazy dla `linux/arm64` (dziś buduje tylko natywną
    architekturę runnera); wdrożenie w osobnym workflow lub grupie `concurrency` bez
    `cancel-in-progress`;
  - **#19:** subdomena i rekord A u obecnego dostawcy DNS — do zrobienia przez właściciela;
  - **#22:** kopie wolumenu przez AWS Backup zamiast Data Lifecycle Manager;
  - **#23:** AWS Budgets z alertem (np. $15/mies.) — przy okazji jedno z zadań dających
    dodatkowe $20 kredytu.
- **Działanie po stronie właściciela przed końcem Free plan:** świadomie przejść na
  **Paid plan** w AWS Settings przed upływem 6 miesięcy od założenia konta, inaczej konto
  i dane zostaną zawieszone, a po 90 dniach usunięte. Warto ustawić przypomnienie z datą
  wygaśnięcia kredytów.

## Źródła

- [Sign up for AWS (new)](https://docs.aws.amazon.com/accounts/latest/reference/sign-in-new.html) — projekty, organizacja, AWS Settings
- [Create a project in AWS Settings](https://docs.aws.amazon.com/accounts/latest/reference/create-project.html)
- [AWS Regions for your projects](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html) — przydział regionu według kraju (Polska → `eu-north-1`)
- [Supported AWS services for Sign up for AWS (new)](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html) — usługi dostępne i niedostępne w projektach
- [Connect an AI coding tool](https://docs.aws.amazon.com/accounts/latest/reference/connect-ai-coding-tool.html) — `aws login --profile` i sesje projektów
- [Create an IAM user](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html) — brak użytkowników IAM z konsolą w nowym interfejsie
- [Track your Free Tier usage for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html) — typy instancji i zasady Free plan dla kont po 15.07.2025
- [AWS Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/) — zawieszenie i usunięcie konta, kredyty po przejściu na Paid plan
- [AWS Free Tier: $200 credits and 6-month free plan](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/)
- [Amazon EC2 On-Demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) — `t4g.micro` w `eu-north-1` i `eu-central-1`
- [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/) — opłata za publiczny IPv4
- [AWS App Runner availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)
- [Amazon ECS Express Mode](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html) — koszt to Fargate + ALB
- [Lightsail billing FAQ](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html) — 90-dniowy okres próbny
- [db.t4g.micro pricing (Bytebase)](https://www.bytebase.com/dbcost/rds/instance/db.t4g.micro/) — orientacyjna cena RDS
