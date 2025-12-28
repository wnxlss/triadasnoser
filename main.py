# main.py
import os
import asyncio
import logging
import random
import string
from datetime import datetime, timedelta
from html import escape
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest
import aiofiles
from database import User
import repka

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token="8459442034:AAFEMEAR0HIXStRtmVaBBD5QaDcSUEzlrHo")
dp = Dispatcher()
router = Router()
ChanID = -1002982718188
Channel = 'https://t.me/+o9du0e6miDJkNzgy'

ADMIN_LOG_FORMAT = (
    "🩸 Новая жалоба от пользователя:\n"
    "🩸 ID: {user_id} \n"
    "🩸 Username: @{username} \n"
    "🩸 Ссылка: {link} \n"
    "🩸 Причина: {reason} \n"
    "🩸 Результат:\n {result} "
)

ADMIN_ACTION_LOG_FORMAT = (
    "🩸 Действие администратора:\n"
    "🩸 Действие: {action}\n"
    "🩸 Детали: {details}" 
)

ADMIN_USERS = [7910618692]
ADMIN_USERNAME = "@scambaseRF"

class UserState(StatesGroup):
    waiting_for_link = State()
    waiting_for_reason = State()
    waitforinfo = State()

class Dp(StatesGroup):
    text = State()

async def send_admin_log(user_id: int, username: str, link: str, reason: str, result: str):
    log_message = ADMIN_LOG_FORMAT.format(
        user_id=user_id,
        username=username or "нет username",
        link=link,
        reason=reason,
        result=result
    )
    
    for admin_id in ADMIN_USERS:
        try:
            await bot.send_message(admin_id, log_message)
        except Exception as e:
            logger.error(f"Не удалось отправить лог админу {admin_id}: {e}")

async def log_admin_action(action: str, details: str):
    log_message = ADMIN_ACTION_LOG_FORMAT.format(
        action=action,
        details=details
    )
    
    for admin_id in ADMIN_USERS:
        try:
            await bot.send_message(admin_id, log_message)
        except Exception as e:
            logger.error(f"Не удалось отправить лог админу {admin_id}: {e}")

async def get_random_template():
    """Получает случайный шаблон из папки shab с ротацией"""
    if not hasattr(get_random_template, "used_templates"):
        get_random_template.used_templates = []
        get_random_template.all_templates = []
        
        if not os.path.exists("shab"):
            os.makedirs("shab")
            logger.error("Папка 'shab' создана. Добавьте в неё шаблоны в формате .txt!")
        
        for filename in os.listdir("shab"):
            if filename.endswith(".txt"):
                try:
                    with open(os.path.join("shab", filename), "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            get_random_template.all_templates.append(content)
                            logger.info(f"Загружен шаблон: {filename}")
                        else:
                            logger.warning(f"Файл {filename} пуст!")
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла {filename}: {e}")
    
    if not get_random_template.all_templates:
        logger.error("В папке 'shab' нет шаблонов. Будет использован стандартный текст.")
        return "Пользователь нарушает правила Telegram. Прошу принять меры."
    
    if len(get_random_template.used_templates) >= len(get_random_template.all_templates):
        logger.info("Сброс использованных шаблонов (новый цикл)")
        get_random_template.used_templates = []
    
    available_templates = [t for t in get_random_template.all_templates 
                         if t not in get_random_template.used_templates]
    
    if not available_templates:
        available_templates = get_random_template.all_templates.copy()
        get_random_template.used_templates = []
    
    selected_template = random.choice(available_templates)
    get_random_template.used_templates.append(selected_template)
    
    logger.info(f"Выбран шаблон: {selected_template[:50]}...")
    return selected_template

def get_restart_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Перезапустить бота")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

@router.callback_query(F.data == "spm")
async def spsk(call: CallbackQuery, state: FSMContext):
    executor_id = call.from_user.id 
    if executor_id not in ADMIN_USERS:
        try:
            await call.answer("❌ Нет доступа")
        except:
            await call.message.reply("❌ Нет доступа")
        return
    
    try:
        await call.message.edit_text('Введи текст рассылки')
    except TelegramBadRequest:
        await call.message.answer('Введи текст рассылки')
    await state.set_state(Dp.text)

@router.message(StateFilter(Dp.text))
async def spam1(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer('Спам запущен', reply_markup=get_restart_keyboard())

    ok = 0
    for x in User.select():
        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text=f"💻 Канал", url=Channel)
            await bot.send_message(x.user_id, msg.text, reply_markup=keyboard.as_markup())
            ok += 1
        except:
            pass
    
    await log_admin_action(
        "Массовая рассылка",
        f"Админ {msg.from_user.id} отправил рассылку {ok} пользователям\nТекст: {msg.text}"
    )
    
    await msg.answer(f'Успешно отправленно: {str(ok)}', reply_markup=get_restart_keyboard())

@router.message(Command("admin"))
async def admin(msg: types.Message):
    executor_id = msg.from_user.id 
    if executor_id not in ADMIN_USERS:
        await msg.reply("Доступ запрещен.")
        return
    await msg.delete()
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=f"📧 Рассылка", callback_data=f"spm")
    keyboard.button(text=f"📰 Список пользователей", callback_data=f"spsk")
    keyboard.button(text=f"🔼 Управление подписками", callback_data=f"manage_subs")
    keyboard.adjust(1)
    await msg.answer(f"😎 Добро пожаловать в админ панель! {ADMIN_USERNAME}", reply_markup=keyboard.as_markup())

@router.callback_query(F.data == "manage_subs")
async def manage_subs(call: CallbackQuery):
    executor_id = call.from_user.id
    if executor_id not in ADMIN_USERS:
        await call.answer("❌ Нет доступа")
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=f"ℹ️ Инструкция", callback_data=f"subs_help")
    keyboard.button(text=f"📋 Список подписчиков", callback_data=f"subs_list")
    keyboard.adjust(1)
    
    await call.message.answer(
        "🔼 Управление подписками\n\n"
        "Используйте команды:\n"
        "/up [id] [days] - выдать подписку\n"
        "/onup [id] - отменить подписку",
        reply_markup=keyboard.as_markup()
    )

@router.message(Command("up"))
async def grant_subscription(msg: types.Message):
    executor_id = msg.from_user.id
    if executor_id not in ADMIN_USERS:
        await msg.reply("❌ Нет доступа")
        return
    
    args = msg.text.split()
    if len(args) < 3:
        await msg.reply("❌ Неверный формат. Используйте: /up [id] [days]")
        return
    
    try:
        user_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await msg.reply("❌ ID и дни должны быть числами")
        return
    
    user = User.get_or_none(User.user_id == user_id)
    if not user:
        await msg.reply("❌ Пользователь не найден")
        return
    
    subscription_end = datetime.now() + timedelta(days=days)
    user.activateduntil = subscription_end
    user.save()
    
    await msg.reply(f"✅``` Пользователю {user_id} выдана подписку на {days} дней```" , parse_mode="markdown", reply_markup=get_restart_keyboard())
    await bot.send_message(user_id, f"```🎉 Вам выдана подписку на {days} дней!```" , parse_mode="markdown")
    
    await log_admin_action(
        "Выдача подписки",
        f"Админ {executor_id} выдал подписку пользователю {user_id} на {days} дней"
    )

@router.message(Command("onup"))
async def revoke_subscription(msg: types.Message):
    executor_id = msg.from_user.id
    if executor_id not in ADMIN_USERS:
        await msg.reply("❌ Нет доступа")
        return
    
    args = msg.text.split()
    if len(args) < 2:
        await msg.reply("❌ Неверный формат. Используйте: /onup [id]")
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await msg.reply("❌ ID должен быть числом")
        return
    
    user = User.get_or_none(User.user_id == user_id)
    if not user:
        await msg.reply("❌ Пользователь не найден")
        return
    
    user.activateduntil = None
    user.save()
    
    await msg.reply(f"```✅ Подписка пользователя {user_id} отменена```", parse_mode="markdown", reply_markup=get_restart_keyboard())
    await bot.send_message(user_id, "```❌ Ваша подписка была отменена администратором```", parse_mode="markdown")
    
    await log_admin_action(
        "Отмена подписки",
        f"Админ {executor_id} отменил подписку пользователя {user_id}"
    )

@router.callback_query(F.data == "spsk")
async def spsk(call: CallbackQuery):
    executor_id = call.from_user.id
    if executor_id not in ADMIN_USERS:
        await call.answer("❌ Нет доступа")
        return

    with open("list.txt", "w") as f:
        for user in User.select():
            f.write(f"{user.user_id} ; Last Used {user.last_used}\n")

    file = FSInputFile("list.txt")
    await bot.send_document(call.message.chat.id, file, reply_markup=get_restart_keyboard())
    
    await log_admin_action(
        "Запрос списка пользователей",
        f"Админ {executor_id} запросил список пользователей"
    )

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    fromuser = message.from_user

    user = User.get_or_none(User.user_id == user_id)
    infobot = await bot.get_me()
    bot_username = infobot.username

    if user:
        welc = (
            f"```TRIADA_SNOS``` Привет {escape(message.from_user.full_name)}!\n\nОткрой новые возможности по низким ценам\n"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=f"💻 Перейти в TRIADA", callback_data=f"bn")
        keyboard.button(text=f"🆘 Админ", callback_data=f"sup")
        keyboard.button(text=f"🗽 Профиль", callback_data=f"prof")
        keyboard.button(text=f"📝 Отзывы", url="https://t.me/+crqwVgn7bGNmNTAy")
        keyboard.button(text=f"📚 Инструкция и правила", url="https://t.me/+T8QjzQltFbw2OTVi")
        keyboard.adjust(2)
        
        try:
            if os.path.exists("banner.png"):
                async with aiofiles.open("banner.png", "rb") as f:
                    photo = FSInputFile(f.name)
                    await message.answer_photo(
                        photo=photo,
                        caption=welc,
                        parse_mode="markdown",
                        reply_markup=keyboard.as_markup(),
                        disable_web_page_preview=True
                    )
            else:
                await message.answer(
                    welc,
                    parse_mode="markdown",
                    reply_markup=keyboard.as_markup(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await message.answer(
                welc,
                parse_mode="markdown",
                reply_markup=keyboard.as_markup(),
                disable_web_page_preview=True
            )
    else:
        user = User.create(
            user_id=user_id,
            last_used=datetime.now(),
            referral_code=''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
            refcount=0,
            activateduntil=None
        )

        mesgg = await message.answer(
            "*Вы успешно зарегистрированы в TRIADA!*\n"
            "*Пожалуйста прочите https://t.me/+T8QjzQltFbw2OTVi , и потом нажмите /start.*", 
            parse_mode='markdown'
        )
        await mesgg.pin()
        
        await log_admin_action(
            "Новый пользователь",
            f"Новый пользователь: {user_id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Username: @{message.from_user.username or 'нет'}"
        )

@router.message(F.text == "🔄 Перезапустить бота")
async def restart_bot(message: Message):
    await cmd_start(message)

@router.callback_query(F.data == "bn")
async def bn(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    
    if user is None:
        try:
            await call.message.edit_text('❌ *юзер не найден!*', parse_mode="Markdown")
        except TelegramBadRequest:
            await call.answer('❌ юзер не найден!')
        return
    
    if user_id not in ADMIN_USERS:
        if user.activateduntil is None or user.activateduntil < datetime.now():
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="💳 Купить подписку", callback_data="buy_subscription")
            try:
                await call.message.edit_text(
                    "❌ У вас нет активной подписки!\n\n"
                    "*Для отправки жалоб требуется подписка.*\n"
                    f"*Обратитесь к продавцу* {ADMIN_USERNAME} *для получения подписки.*",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="markdown"
                )
            except TelegramBadRequest:
                await call.message.answer(
                    "❌ У вас нет активной подписки!\n\n"
                    "*Для отправки жалоб требуется подписка.*\n"
                    f"*Обратитесь к продавцу* {ADMIN_USERNAME} *для получения подписки.*",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="markdown"
                )
            return

    current_time = datetime.now()
    if user_id not in ADMIN_USERS:
        if current_time - user.last_used < timedelta(minutes=2):
            remaining_time = timedelta(minutes=2) - (current_time - user.last_used)
            try:
                await call.message.edit_text(
                    f'❌ Жди {remaining_time.seconds // 60} минут и {remaining_time.seconds % 60} секунд!',
                    parse_mode="Markdown"
                )
            except TelegramBadRequest:
                await call.answer(f'❌ Жди {remaining_time.seconds // 60} минут и {remaining_time.seconds % 60} секунд!')
            return
        user.last_used = current_time
        user.save()

    await call.message.answer("`📧 Отправьте ссылку... (по типу` https://t.me/Bro9ichat/894645)" , parse_mode="markdown", reply_markup=get_restart_keyboard())
    await state.set_state(UserState.waiting_for_link)

@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(call: CallbackQuery):
    try:
        await call.message.edit_text(
            f"Для покупки подписки обратитесь к администратору: ```{ADMIN_USERNAME}```\n\n"
            "Цена подписки написана в нашем канале https://t.me/+iiRbUNHfe4xjNWIy\n"
            "Подписка дает возможность:\n\n"
            "🥵 Сносить аккаунты \n"
            "🥵 Фризить аккаунты",
            parse_mode="markdown"
        )
    except TelegramBadRequest:
        await call.message.answer(
            f"Для покупки подписки обратитесь к администратору: ```{ADMIN_USERNAME}```\n\n"
            "Цена подписки написана в нашем канале https://t.me/+iiRbUNHfe4xjNWIy\n"
            "Подписка дает возможность:\n\n"
            "❄️ Сносить аккаунты \n"
            "❄️ Фризить аккаунты",
            parse_mode="markdown",
            reply_markup=get_restart_keyboard()
        )

@router.message(F.text.startswith("https://"), StateFilter(UserState.waiting_for_link))
async def handle_link_submission(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    username = message.from_user.username or "Нет username"

    if user:
        if user_id not in ADMIN_USERS:
            if user.activateduntil is None or user.activateduntil < datetime.now():
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="💳 Купить подписку", callback_data="buy_subscription")
                await message.answer(
                    "❌ У вас нет активной подписки!\n\n"
                    "Для отправки сноса требуется подписка.\n"
                    f"Обратитесь к администратору {ADMIN_USERNAME} для получения подписки.",
                    reply_markup=keyboard.as_markup()
                )
                await state.clear()
                return

        link = message.text
        template = await get_random_template()
        
        processing_message = await message.answer(
            f"```INFO:```\n"
            f"Происходит снос❄️\n"
            f"✅ Запрос отправлен на {link} \n"
            f"📨 Причина: Other \n"
            f"🧿 Тип запроса: ACT \n\n"
            f"⚠️ Окончательное решение остаётся за администрацией Telegram.\n"
            f"[Отзывы](https://t.me/+0iaLY-fx429lMTky) ❄️ [Канал](https://t.me/+AG58eZESVoVlNTU6) ❄️ [Поддержка.](http://scambaseRF.t.me/)", 
            parse_mode="markdown",
            reply_markup=get_restart_keyboard()
        )

        async def update_callback(gcount, scount):
            try:
                await processing_message.edit_text(
            f"```INFO:```\n"
            f"Происходит снос❄️\n"
            f"✅ Запрос отправлен на {link} \n"
            f"📨 Причина: Other \n"
            f"🧿 Тип запроса: ACT \n\n"
            f"⚠️ Окончательное решение остаётся за администрацией Telegram.\n"
            f"[Отзывы](https://t.me/+0iaLY-fx429lMTky) ❄️ [Канал](https://t.me/+AG58eZESVoVlNTU6) ❄️ [Поддержка.](http://scambaseRF.t.me/)",
            parse_mode="markdown",
                )
            except TelegramBadRequest:
                pass

        # Проверяем существование модуля repka
        try:
            result = await repka.report_message(
                link, 
                "other", 
                update_callback, 
                user_id, 
                username
            )
        except AttributeError as e:
            logger.error(f"Ошибка в модуле repka: {e}")
            result = f"Ошибка отправки жалоб: {e}"
        except Exception as e:
            logger.error(f"Ошибка при отправке жалоб: {e}")
            result = f"Ошибка при отправке жалоб: {e}"
        
        await send_admin_log(
            user_id=user_id,
            username=username,
            link=link,
            reason="other",
            result=result
        )

        await state.clear()
    else:
        await message.answer("Вы не авторизованы.", reply_markup=get_restart_keyboard())

@router.message(StateFilter(UserState.waitforinfo))
async def infothingy(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = User.get_or_none(User.user_id == user_id)

    if user:
        await message.answer('Подождите...', reply_markup=get_restart_keyboard())
        link = message.text
        try:
            result = await repka.telemail(link)
        except Exception as e:
            logger.error(f"Ошибка в telemail: {e}")
            result = f"Ошибка обработки: {e}"
        await message.answer(f"Обработано: \n{result}", parse_mode="HTML", reply_markup=get_restart_keyboard())
        await state.clear()
    else:
        await message.answer("Нельзя тебе.", reply_markup=get_restart_keyboard())

@router.callback_query(F.data == "prof")
async def prof(call: CallbackQuery):
    user_id = call.from_user.id
    user = User.get_or_none(User.user_id == user_id)
    
    if not user:
        await call.answer("❌ Пользователь не найден")
        return
    
    await call.answer('Подождите... получаю информацию.')
    
    if user.activateduntil:
        sub_status = f"✅ Активна до: {user.activateduntil.strftime('%Y-%m-%d %H:%M')}"
    else:
        sub_status = "❌ Не активна"
    
    try:
        await call.message.edit_text(
            f'📝 Ваш профиль :\n\n'
            f'🆔 ID : {user_id}\n'
            f'💎 Подписка: {sub_status}',
            parse_mode='markdown'
        )

    except TelegramBadRequest:
        await call.message.answer(
            f'📝 Ваш профиль :\n\n'
            f'🆔 ID : {user_id}\n'
            f'💎 Подписка: {sub_status}',
            parse_mode='markdown',
            reply_markup=get_restart_keyboard()
        )

@router.callback_query(F.data == "sup")
async def sup(call: CallbackQuery):
    try:
        await call.message.edit_text(
            f"`📧 Связь с админом\n\nДля связи:` {ADMIN_USERNAME}",
            parse_mode="markdown"
        )
    except TelegramBadRequest:
        await call.message.answer(
            f"`📧 Связь с админом\n\nДля связи:` {ADMIN_USERNAME}",
            parse_mode="markdown",
            reply_markup=get_restart_keyboard()
        )

async def main():
    dp.include_router(router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    # Проверяем существование необходимых файлов
    if not os.path.exists("shab"):
        os.makedirs("shab")
        logger.warning("Папка 'shab' создана. Добавьте в неё шаблоны в формате .txt!")
    
    # Запускаем бота
    asyncio.run(main())