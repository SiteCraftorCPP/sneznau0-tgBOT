import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import BOT_TOKEN
from database import create_tables, get_all_sections
from navigation import router as navigation_router
from admin import router as admin_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(navigation_router)

def get_main_keyboard():
    sections = get_all_sections()
    kb = []
    for name, code in sections:
        icon = "🔧"
        if "Электро" in name: icon = "⚡"
        elif "Прибор" in name: icon = "📊"
        elif "Радио" in name: icon = "📻"
        button_text = f"{icon} {code}. {name.upper()}"
        kb.append([KeyboardButton(text=button_text)])
    kb.append([KeyboardButton(text="🔍 БЫСТРЫЙ ПОИСК")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Выберите раздел:", reply_markup=get_main_keyboard())

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer("Выберите раздел:", reply_markup=get_main_keyboard())

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
    create_tables()
    from config import ADMIN_IDS
    print("Бот запущен. ADMIN_IDS:", ADMIN_IDS or "(пусто — задай в .env: ADMIN_IDS=твой_telegram_id)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
