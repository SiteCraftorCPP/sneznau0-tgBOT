import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN
from database import create_tables, get_all_sections, create_connection
from navigation import router as navigation_router
from admin import router as admin_router

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Порядок роутеров: сначала админка — чтобы в админке 4.1/4.2/4.3 вели в список с редактированием (manage_sub_)
dp.include_router(admin_router)
dp.include_router(navigation_router)

# Клавиатура главного меню (динамическая)
def get_main_keyboard():
    sections = get_all_sections()
    kb = []
    
    # Добавляем кнопки разделов из БД
    for name, code in sections:
        icon = "🔧"
        if "Электро" in name: icon = "⚡"
        elif "Прибор" in name: icon = "📊"
        elif "Радио" in name: icon = "📻"
        
        button_text = f"{icon} {code}. {name.upper()}"
        kb.append([KeyboardButton(text=button_text)])

    # Добавляем системные кнопки
    kb.append([KeyboardButton(text="🔍 БЫСТРЫЙ ПОИСК")])
    kb.append([KeyboardButton(text="💡 ПРЕДЛОЖИТЬ НЕИСПРАВНОСТЬ")])
    kb.append([KeyboardButton(text="❓ ПОМОЩЬ")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Выберите раздел:",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды /menu
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer(
        "Выберите раздел:",
        reply_markup=get_main_keyboard()
    )

# === ОБРАБОТЧИКИ МЕНЮ ===
@dp.message(F.text == "❓ ПОМОЩЬ")
async def cmd_help(message: types.Message):
    help_text = (
        "Справка по боту:\n"
        "/start - Начало работы\n"
        "/menu - Главное меню\n"
        "/search <текст> - Поиск\n"
        "/suggest - Предложить неисправность"
    )
    await message.answer(help_text)

async def main():
    # Создаем таблицы при запуске
    create_tables()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
