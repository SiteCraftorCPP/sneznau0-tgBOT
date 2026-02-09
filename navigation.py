from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from database import create_connection
from search import search_subsections

router = Router()


class SearchStates(StatesGroup):
    waiting_query = State()

async def show_section_subsections(message: types.Message, section_code: str):
    conn = create_connection()
    if not conn:
        await message.answer("Ошибка подключения к базе данных.")
        return
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sections WHERE code = ?", (section_code,))
    section = cursor.fetchone()
    if not section:
        conn.close()
        return
    section_id, section_name = section
    cursor.execute("SELECT id, name FROM subsections WHERE section_id = ?", (section_id,))
    subs = cursor.fetchall()
    conn.close()

    kb = []
    for s_id, name in subs:
        kb.append([InlineKeyboardButton(text=f"📂 {name}", callback_data=f"sub_click_{s_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="close_msg")])

    text = f"📂 Раздел: **{section_name}**"
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")


async def show_subsection_content(callback: CallbackQuery, sub_id: int):
    """Показать текст пункта (подраздела) пользователю."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, content, section_id FROM subsections WHERE id = ?", (sub_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await callback.answer("Пункт не найден")
        return
    sub_name, content, section_id = row
    text = f"📂 **{sub_name}**\n\n"
    if content and content.strip():
        text += content
    else:
        text += "⚠ Нет описания."
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_sec_{section_id}")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")


# Быстрый поиск — обрабатываем первыми (по состоянию)
@router.message(F.text.contains("БЫСТРЫЙ ПОИСК"))
async def quick_search_start(message: types.Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_query)
    await message.answer("Введите запрос для поиска по названиям разделов:")

@router.message(SearchStates.waiting_query, F.text)
async def quick_search_run(message: types.Message, state: FSMContext):
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введите непустой запрос.")
        return
    results = search_subsections(query)
    if not results:
        await message.answer("Ничего не найдено.")
        return
    kb = []
    for sub_id, sub_name, section_name in results:
        label = sub_name if len(sub_name) <= 50 else sub_name[:47] + "..."
        kb.append([InlineKeyboardButton(text=f"📂 {label}", callback_data=f"sub_click_{sub_id}")])
    await message.answer(
        f"Найдено: {len(results)}\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )

@router.message(F.text.contains("4.1"), StateFilter("*"))
async def section_electro(message: types.Message, state: FSMContext):
    await state.clear()
    await show_section_subsections(message, "4.1")

@router.message(F.text.contains("4.2"), StateFilter("*"))
async def section_pribor(message: types.Message, state: FSMContext):
    await state.clear()
    await show_section_subsections(message, "4.2")

@router.message(F.text.contains("4.3"), StateFilter("*"))
async def section_radio(message: types.Message, state: FSMContext):
    await state.clear()
    await show_section_subsections(message, "4.3")

@router.callback_query(F.data.startswith("sub_click_"))
async def process_sub_click(callback: CallbackQuery):
    """Главное меню — только просмотр. Редактирование только через /admin."""
    sub_id = int(callback.data.split("_")[2])
    await show_subsection_content(callback, sub_id)

@router.callback_query(F.data == "close_msg")
async def close_message(callback: CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data.startswith("back_to_sec_"))
async def back_to_section(callback: CallbackQuery):
    section_id = int(callback.data.split("_")[3])
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM sections WHERE id = ?", (section_id,))
    code = cursor.fetchone()[0]
    conn.close()
    await callback.message.delete()
    await show_section_subsections(callback.message, code)
