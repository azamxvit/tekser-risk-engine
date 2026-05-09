# Tekser Risk Engine

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.10_|_3.11_|_3.12+-blue)
![Stack](https://img.shields.io/badge/stack-Supabase%20%7C%20Requests%20%7C%20BS4%20%7C%20dotenv-lightgrey)

**Tekser Risk Engine** (каз. «тексер» — *тексеру*, проверять) — ETL-сервис для продукта **Tekser**: собирает тексты из открытых веб-страниц и публичных Telegram-превью, извлекает **казахстанские** номера телефонов (`+77…`), классифицирует тип мошенничества по ключевым словам и **батчем** записывает данные в **Supabase** (`public.phone_numbers`, опционально `public.reports`).

---

## Key features

- **Web vacuum:** список URL из `SCRAPER_URLS`; поддержка пагинации через `{page}` (диапазон задаётся `SCRAPER_PAGES`).
- **Telegram без API:** публичный HTML `https://t.me/s/<channel>` — без `TG_API_ID` / сессий; каналы в `TG_PUBLIC_CHANNELS`.
- **KZ-only extractor:** в БД попадают только номера вида `+77XXXXXXXXX` (отсекаются российские `+73…`, `+79…` и т.д.).
- **Batch upsert:** один проход по `phone_numbers` с `on_conflict=number` — сумма `report_count`, `last_reported = max`, «сильнее» выигрывает `fraud_type`; `risk_score` / `is_verified` ETL не трогает.
- **Daily dedup:** при `DAILY_REPORT_DEDUP=true` повторный запуск в тот же **UTC-день** не накручивает `report_count`, если `last_reported` уже сегодня (анти-накрутка на статических страницах).
- **Secrets safety:** `load_dotenv(..., override=True)` из корня репо; проверка, что в `SUPABASE_SERVICE_ROLE_KEY` не anon/publishable — иначе падение с понятной ошибкой до запросов к API.
- **CI/CD:** GitHub Actions — ежедневный запуск + ручной `workflow_dispatch` (секреты и variables описаны ниже).

---

## Tech stack

| Layer | Choice |
|--------|--------|
| Language | Python 3.10+ (рекомендуется 3.11 в CI) |
| HTTP / HTML | `requests`, `beautifulsoup4` |
| Database | Supabase (PostgREST), `supabase` Python client |
| Config | `python-dotenv`, `.env` в корне (не коммитится) |
| Scheduling | GitHub Actions `cron` |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  scrapers/      │     │  core/           │
│  web_scraper    │────▶│  extractor       │──┐
│  tg_scraper     │     │  classifier      │  │
└────────┬────────┘     └────────┬─────────┘  │
         │ raw texts             │ phones +   │
         │                       │ fraud_type │
         ▼                       ▼            │
┌────────────────────────────────────────────┴──┐
│  main.py — collect_texts → texts_to_records   │
└─────────────────────┬───────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  db/supabase_client.py                           │
│  upsert_phone_numbers() | insert_reports() *     │
└─────────────────────┬───────────────────────────┘
                      ▼
              Supabase PostgreSQL
         phone_numbers (+ optional reports)
```

\* `insert_reports` только при `WRITE_REPORTS=true`.

---

## Getting started

### 1. Clone

```bash
git clone <your-repo-url>
cd tekser-risk-engine
```

### 2. Virtualenv and dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment

Скопируйте шаблон и заполните секреты:

```bash
cp .env.example .env
```

Обязательно:

| Variable | Role |
|----------|------|
| `SUPABASE_URL` | URL проекта Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | **Secret** `service_role` JWT (не publishable / не anon) |

Источники (хотя бы один непустой):

| Variable | Role |
|----------|------|
| `SCRAPER_URLS` | Список URL через запятую; в строке можно `{page}` |
| `SCRAPER_PAGES` | Сколько подставить страниц для `{page}` (по умолчанию в примере — `10`) |
| `TG_PUBLIC_CHANNELS` | Каналы через запятую (`orda_kz`, `@name`, полный `https://t.me/...`) |

Поведение:

| Variable | Role |
|----------|------|
| `DAILY_REPORT_DEDUP` | `true` / `false` — дедуп прироста `report_count` в пределах UTC-дня |
| `WRITE_REPORTS` | `true` — дополнительно писать в `public.reports` |

### 4. Run ETL

Из **корня** репозитория (чтобы подтянулся `src` как пакет при импортах из `main`):

```bash
python src/main.py
```

Windows PowerShell:

```powershell
Set-Location path\to\tekser-risk-engine
python src\main.py
```

В логах ожидайте строки вида: `phone_numbers: received=… unique=… upserted=… dedup_skipped=…`.

---

## GitHub Actions

Workflow: `.github/workflows/daily_scraper.yml` — расписание `0 2 * * *` (UTC) и ручной запуск.

**Secrets** (Settings → Secrets and variables → Actions):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SCRAPER_URLS`
- `TG_PUBLIC_CHANNELS`

**Variables** (та же страница, вкладка Variables):

- `SCRAPER_PAGES` (например `10`)
- `WRITE_REPORTS` (например `false`)
- `DAILY_REPORT_DEDUP` (например `true`)

---

## Project layout

```
tekser-risk-engine/
├── src/
│   ├── main.py                 # Точка входа ETL
│   ├── core/
│   │   ├── extractor.py        # Regex + нормализация KZ E.164
│   │   └── classifier.py     # fraud_type по ключевым словам
│   ├── db/
│   │   └── supabase_client.py # load_dotenv, upsert, optional reports
│   └── scrapers/
│       ├── web_scraper.py      # HTTP + видимый текст страницы
│       └── tg_scraper.py       # t.me/s/<channel> публичное превью
├── .github/workflows/
│   └── daily_scraper.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎥 Demo

*(Coming soon!)*

---

## License

*(Coming soon!)*
