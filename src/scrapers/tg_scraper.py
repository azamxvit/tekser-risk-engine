import os
import asyncio
import logging
from telethon.sync import TelegramClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")
TARGET_CHANNELS = ['@scammers_kz_example', '@zhaloby_astana_example'] 

async def fetch_tg_messages(limit: int = 50) -> list:
    """Асинхронно собирает последние сообщения из заданных ТГ-каналов."""
    if not API_ID or not API_HASH:
        logger.warning("⚠️ Не заданы TG_API_ID или TG_API_HASH. Пропуск Telegram парсера.")
        return []

    texts = []
    client = TelegramClient('tekser_session', API_ID, API_HASH)

    await client.start()
    logger.info("📱 Telegram Client успешно запущен!")

    for channel in TARGET_CHANNELS:
        try:
            logger.info(f"📥 Чтение чата: {channel}")
            async for message in client.iter_messages(channel, limit=limit):
                if message.text:
                    texts.append(message.text)
        except Exception as e:
            logger.error(f"❌ Ошибка чтения чата {channel}: {e}")

    await client.disconnect()
    return texts

def get_telegram_data() -> list:
    """Синхронная обертка для вызова из главного синхронного файла main.py"""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fetch_tg_messages())
    except Exception as e:
        logger.error(f"❌ Критическая ошибка Telegram парсера: {e}")
        return []