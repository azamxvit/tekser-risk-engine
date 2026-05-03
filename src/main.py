import logging
import requests
from bs4 import BeautifulSoup
from core.extractor import extract_kz_phones
from core.classifier import get_scam_type
from db.supabase_client import load_to_db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_web_example():
    """Пример простого парсера веб-страницы с жалобами"""
    # В реальности тут будет цикл по страницам zhaloby.kz и т.д.
    # Сейчас имитируем полученные данные для старта
    logger.info("Начинаем парсинг веб-источников...")
    mock_data = [
        "Звонили с номера 8 705 111-22-33, сказали что с Каспи банка, пытались украсть деньги.",
        "КНБ беспокоит. Майор Иванов. +7(777)9998877. Мошенники чистой воды!",
        "Опять спам с +77273332211, реклама курсов."
    ]
    return mock_data

def run_etl_pipeline():
    logger.info("🚀 Запуск Tekser ETL пайплайна...")
    
    # 1. Extract (Получаем сырые тексты)
    raw_texts = scrape_web_example()
    # tg_texts = scrape_telegram() # Место для подключения Telethon
    
    total_processed = 0
    
    for text in raw_texts:
        # 2. Extract (Достаем номера)
        phones = extract_kz_phones(text)
        
        # 3. Transform (Определяем тип)
        scam_type = get_scam_type(text)
        
        # 4. Load (Грузим в БД)
        for phone in phones:
            load_to_db(phone=phone, scam_type=scam_type, description=text)
            total_processed += 1
            
    logger.info(f"🎉 Пайплайн завершен. Обработано номеров: {total_processed}")

if __name__ == "__main__":
    run_etl_pipeline()