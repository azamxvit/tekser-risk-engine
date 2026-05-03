# 🛡️ Tekser-Risk-Engine - Scammer Database Aggregator

Tekser-Risk-Engine (каз. "проверять") — это ETL-пайплайн на Python для приложения Tekser. 
Он автоматически собирает номера мошенников из открытых Telegram-чатов и сайтов с отзывами, классифицирует их и загружает в базу данных Supabase.

## 🏗 Архитектура
1. **Extract (Scrapers):** Сбор сырых текстов через `BeautifulSoup` и `Telethon`.
2. **Transform (Core):** Извлечение валидных номеров (`+7\d{10}`) через Regex и определение типа мошенничества по ключевым словам.
3. **Load (DB):** Безопасный UPSERT в Supabase.

## 🚀 Локальный запуск

1. Клонируйте репозиторий:
   ```bash
   git clone <your-repo-url>
   cd tekser