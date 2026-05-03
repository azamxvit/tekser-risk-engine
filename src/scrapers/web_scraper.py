import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_complaints_website() -> list:
    """
    Собирает тексты жалоб с веб-сайтов (пример на базе абстрактного сайта отзывов).
    Возвращает список строк (текстов отзывов).
    """
    texts = []
    
    # URL для примера (нужно заменить на реальную страницу с жалобами)
    # Например: https://zhaloby.kz/категория/мошенники
    target_url = "https://example.com/scam-reports" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        logger.info(f"🌐 Парсинг сайта: {target_url}")
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            comments = soup.find_all('div', class_='comment-text') 
            
            for comment in comments:
                text = comment.get_text(strip=True)
                if text:
                    texts.append(text)
                    
            logger.info(f"✅ Успешно собрано отзывов с сайта: {len(texts)}")
        else:
            logger.warning(f"⚠️ Ошибка доступа к сайту. Код: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка веб-парсера: {e}")
        
    return texts