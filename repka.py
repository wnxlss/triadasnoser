import os
import asyncio
import random
from telethon import TelegramClient, errors
from telethon.tl.functions.messages import ReportRequest
from telethon import types as telethon_types
from re import compile as compile_link
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sesspath = "./sessions/"
API_ID = 24986768
API_HASH = '8c0f3fc3aa16086f2ed31825f2820194'
CONNECT_TIMEOUT = 5 #настройка скорости отправки жб
MAX_RETRIES = 3
MAX_CONCURRENT_SESSIONS = 10
BASE_DELAY = 1.0
RANDOM_DELAY_RANGE = (0.3, 1.5)
BATCH_DELAY = 0.0

# Кэш шаблонов для быстрого доступа
TEMPLATE_CACHE = []

def load_templates():
    """Загружает все шаблоны из папки shab в кэш"""
    global TEMPLATE_CACHE
    if TEMPLATE_CACHE:
        return
    
    if not os.path.exists("shab"):
        os.makedirs("shab")
        logger.warning("Папка 'shab' создана. Добавьте шаблоны!")
    
    for filename in os.listdir("shab"):
        if filename.endswith(".txt"):
            try:
                with open(os.path.join("shab", filename), "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        TEMPLATE_CACHE.append(content)
                        logger.info(f"Загружен шаблон: {filename}")
            except Exception as e:
                logger.error(f"Ошибка чтения шаблона {filename}: {e}")
    
    if not TEMPLATE_CACHE:
        logger.warning("Нет шаблонов! Будет использован стандартный текст")
        TEMPLATE_CACHE.append("Пользователь нарушает правила Telegram. Прошу принять меры.")

def get_random_template_for_session():
    """Возвращает случайный шаблон для сессии"""
    if not TEMPLATE_CACHE:
        load_templates()
    
    return random.choice(TEMPLATE_CACHE)

async def process_session(session, chat, message_id, tp, update_callback):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            await asyncio.sleep(random.uniform(*RANDOM_DELAY_RANGE))
            
            client = TelegramClient(
                f"{sesspath}{session}",
                API_ID,
                API_HASH,
                device_model='Mac Pro',
                system_version='macOS 10.15',
                app_version='8.4',
                system_lang_code="en-US",
                lang_code="en",
                timeout=CONNECT_TIMEOUT
            )

            try:
                await client.connect()
                if not await client.is_user_authorized():
                    logger.warning(f"Session {session} is not authorized. Skipping.")
                    await client.disconnect()
                    return (0, 1)

                entity = await client.get_entity(chat)
                
                # Получаем уникальный шаблон для КАЖДОЙ сессии
                template = get_random_template_for_session()
                logger.info(f"[{session}] Using template: {template[:50]}...")
                
                await client(ReportRequest(
                    peer=entity,
                    id=[message_id],
                    reason=tp,
                    message=template,
                ))
                logger.info(f"Complaint sent for session {session}")
                await client.disconnect()
                return (1, 0)

            except errors.AuthKeyDuplicatedError:
                logger.error(f"Session {session} is duplicated. Deleting and skipping.")
                os.remove(f"{sesspath}{session}")
                return (0, 1)

            except Exception as e:
                logger.error(f"Error processing session {session}: {e}")
                retries += 1
                if retries >= MAX_RETRIES:
                    return (0, 1)
                await asyncio.sleep(BASE_DELAY * 2)

        except Exception as e:
            logger.error(f"Unexpected error for session {session}: {e}")
            retries += 1
            if retries >= MAX_RETRIES:
                return (0, 1)
            await asyncio.sleep(BASE_DELAY * 2)

    return (0, 1)

async def report_message(link, tyep, update_callback, user_id=None, username=None) -> str:
    if "/c/" in link:
        return "Приват группы не поддерживаются"

    message_link_pattern = compile_link(r'https://t.me/(?P<username_or_chat>.+)/(?P<message_id>\d+)')
    match = message_link_pattern.search(link)
    if not match:
        return "Неверная ссылка."
    
    tp = telethon_types.InputReportReasonOther()
    
    chat = match.group("username_or_chat")
    message_id = int(match.group("message_id"))
    sessions = [s for s in os.listdir(sesspath) if s.endswith(".session")]
    
    gcount = 0
    scount = 0
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SESSIONS)
    
    async def process_with_semaphore(session):
        async with semaphore:
            nonlocal gcount, scount
            new_gcount, new_scount = await process_session(
                session, 
                chat, 
                message_id, 
                tp, 
                update_callback
            )
            gcount += new_gcount
            scount += new_scount
            await update_callback(gcount, scount)
            await asyncio.sleep(random.uniform(0.2, 0.8))

    batch_size = 5
    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        tasks = [process_with_semaphore(session) for session in batch]
        await asyncio.gather(*tasks)
        if i + batch_size < len(sessions):
            await asyncio.sleep(BATCH_DELAY)
    
    result = f'🩸Успешно:{gcount} \n🩸Не успешно: {scount}'
    logger.info(f"Report completed. Link: {link}, Result: {result}")
    return result

async def telemail(link):
    return "Функция telemail временно недоступна"