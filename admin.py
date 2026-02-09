from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS, ADMIN_PASSWORD
from database import create_connection, get_all_sections

router = Router()

class AdminStates(StatesGroup):
    waiting_for_password = State()
    section_selection = State()
    subsection_management = State()
    add_subsection = State()
    edit_subsection_name = State()
    subsection_edit_text = State()  # ожидание текста для подраздела

# === ОБРАБОТЧИКИ АДМИНСКИХ ДЕЙСТВИЙ ИЗ MAIN.PY ===

@router.callback_query(F.data.startswith("delete_sub_"))
async def delete_sub_quick(callback: types.CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split("_")[2])
    
    conn = create_connection()
    cursor = conn.cursor()
    # Получаем section_id и name для возврата
    cursor.execute("SELECT s.id, s.name FROM sections s JOIN subsections sub ON s.id = sub.section_id WHERE sub.id = ?", (sub_id,))
    res = cursor.fetchone()
    section_id, section_name = res if res else (0, "Раздел")
    
    cursor.execute("DELETE FROM subsections WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
    
    await callback.answer("Удалено")
    await callback.message.delete()
    
    # Возвращаем меню подразделов
    await show_subsections_editor(callback.message, section_id, section_name)
    await state.set_state(AdminStates.subsection_management)
    await state.update_data(current_section_id=section_id, current_section_name=section_name)

@router.callback_query(F.data.startswith("rename_sub_"))
async def rename_sub_quick(callback: types.CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split("_")[2])
    await state.update_data(current_sub_id=sub_id)
    
    # Добавляем кнопку отмены
    kb = [[InlineKeyboardButton(text="🔙 Отмена", callback_data=f"cancel_rename_sub_{sub_id}")]]
    await callback.message.edit_text("Введите название:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    await state.set_state(AdminStates.edit_subsection_name)
    await callback.answer()

def _subsection_menu_kb(sub_id: int, section_id: int):
    return [
        [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data=f"edit_sub_text_{sub_id}")],
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_sub_{sub_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_sub_{sub_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_sec_{section_id}")]
    ]

async def show_admin_sub_menu(callback: types.CallbackQuery, sub_id: int):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, section_id FROM subsections WHERE id = ?", (sub_id,))
    res = cursor.fetchone()
    conn.close()
    if not res:
        await callback.answer("Не найден")
        return
    sub_name, section_id = res
    text = f"📂 **{sub_name}**"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=_subsection_menu_kb(sub_id, section_id)), parse_mode="Markdown")

@router.callback_query(F.data.startswith("cancel_rename_sub_"))
async def cancel_rename_sub(callback: types.CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split("_")[3])
    await show_admin_sub_menu(callback, sub_id)
    await state.set_state(AdminStates.subsection_management)

@router.message(AdminStates.edit_subsection_name)
async def rename_sub_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sub_id = data['current_sub_id']
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE subsections SET name = ? WHERE id = ?", (message.text, sub_id))
    conn.commit()
    
    # Получаем инфо для возврата
    cursor.execute("SELECT s.id, s.name FROM sections s JOIN subsections sub ON s.id = sub.section_id WHERE sub.id = ?", (sub_id,))
    res = cursor.fetchone()
    conn.close()
    
    if res:
        section_id, section_name = res
        await message.answer("✅ Переименовано.")
        # Возвращаемся в список подразделов (или можно в меню подраздела, но логичнее в список, чтобы видеть изменение)
        await show_subsections_editor(message, section_id, section_name)
        await state.set_state(AdminStates.subsection_management)
        await state.update_data(current_section_id=section_id, current_section_name=section_name)
    else:
        await message.answer("Ошибка обновления.")
        await state.clear()

# === РЕДАКТИРОВАНИЕ ТЕКСТА ПОДРАЗДЕЛА ===
@router.callback_query(F.data.startswith("edit_sub_text_"))
async def edit_sub_text_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return
    sub_id = int(callback.data.split("_")[3])
    await state.update_data(current_sub_id=sub_id)
    await state.set_state(AdminStates.subsection_edit_text)
    await callback.message.answer("Отправьте текст для этого пункта (текущий будет заменён):")
    await callback.answer()

@router.message(AdminStates.subsection_edit_text)
async def subsection_edit_text_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sub_id = data["current_sub_id"]
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE subsections SET content = ? WHERE id = ?", (message.text, sub_id))
    conn.commit()
    cursor.execute("SELECT s.name FROM sections s JOIN subsections sub ON sub.section_id = s.id WHERE sub.id = ?", (sub_id,))
    section_name_row = cursor.fetchone()
    cursor.execute("SELECT name, section_id FROM subsections WHERE id = ?", (sub_id,))
    row = cursor.fetchone()
    conn.close()
    await message.answer("✅ Текст сохранён.")
    if row:
        sub_name, section_id = row
        section_name = section_name_row[0] if section_name_row else "Раздел"
        await state.update_data(current_section_id=section_id, current_section_name=section_name)
        await state.set_state(AdminStates.subsection_management)
        kb = [
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data=f"edit_sub_text_{sub_id}")],
            [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"rename_sub_{sub_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_sub_{sub_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subs_list")]
        ]
        await message.answer(f"📂 **{sub_name}**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

# === БЫСТРОЕ ДОБАВЛЕНИЕ ПОДРАЗДЕЛА (ИЗ МЕНЮ) ===

@router.callback_query(F.data.startswith("quick_add_sub_"))
async def quick_add_sub_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    section_id = int(callback.data.split("_")[3])
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
    res = cursor.fetchone()
    conn.close()
    
    section_name = res[0] if res else "Раздел"

    await state.update_data(current_section_id=section_id, current_section_name=section_name)
    await callback.message.answer("Введите название:")
    await state.set_state(AdminStates.add_subsection)
    await callback.answer()

# === ВХОД В АДМИНКУ ===

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(
            f"Нет доступа. Ваш Telegram ID: `{message.from_user.id}`. "
            "Добавьте его в .env на сервере: ADMIN_IDS=ваш_id",
            parse_mode="Markdown"
        )
        return
    await message.answer("Введите пароль администратора:")
    await state.set_state(AdminStates.waiting_for_password)

@router.message(AdminStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        await show_main_admin_menu(message)
        await state.set_state(AdminStates.section_selection)
    else:
        await message.answer("❌ Неверный пароль.")

async def show_main_admin_menu(message: types.Message):
    # Показываем те же кнопки, что и в главном меню, но для админа
    sections = get_all_sections()
    kb = []
    for name, code in sections:
        kb.append([KeyboardButton(text=f"{code}. {name}")])
    kb.append([KeyboardButton(text="🔙 ВЫЙТИ ИЗ АДМИНКИ")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Меню:", reply_markup=keyboard)

@router.message(F.text == "🔙 ВЫЙТИ ИЗ АДМИНКИ")
async def admin_exit(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await message.answer("Вы вышли из режима администратора.", reply_markup=types.ReplyKeyboardRemove())

# === УРОВЕНЬ 1: ВЫБОР РАЗДЕЛА -> СПИСОК ПОДРАЗДЕЛОВ ===

async def _do_section_click(message: types.Message, state: FSMContext, text: str):
    if "." not in text or text.count(".") < 2:
        return False
    code = text.split(".")[0] + "." + text.split(".")[1]
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sections WHERE code LIKE ?", (f"{code}%",))
    res = cursor.fetchone()
    conn.close()
    if not res:
        await message.answer("Раздел не найден.")
        return True
    section_id, section_name = res
    await state.update_data(current_section_id=section_id, current_section_name=section_name)
    await show_subsections_editor(message, section_id, section_name)
    await state.set_state(AdminStates.subsection_management)
    return True

@router.message(AdminStates.section_selection)
async def process_section_click(message: types.Message, state: FSMContext):
    await _do_section_click(message, state, message.text)

# Запасной обработчик: админ нажал 4.1/4.2/4.3, но state потерялся (перезапуск VPS и т.п.)
@router.message(~StateFilter(AdminStates.section_selection), F.text.startswith(("4.1.", "4.2.", "4.3.")))
async def process_section_click_fallback(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await _do_section_click(message, state, message.text)

async def show_subsections_editor(message: types.Message, section_id, section_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM subsections WHERE section_id = ?", (section_id,))
    subs = cursor.fetchall()
    conn.close()
    
    text = f"**{section_name}**"
    
    kb = []
    # Кнопки существующих подразделов
    for s_id, name in subs:
        # При нажатии открываем меню действий с подразделом (Ред/Удал/Открыть)
        kb.append([InlineKeyboardButton(text=f"📂 {name}", callback_data=f"manage_sub_{s_id}")])
    
    # Кнопка добавления
    kb.append([InlineKeyboardButton(text="➕ ДОБАВИТЬ ПОДРАЗДЕЛ", callback_data="add_new_sub")])
    
    # Кнопка Назад (закрывает сообщение, так как разделы в нижнем меню)
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="close_admin_msg")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "close_admin_msg")
async def close_admin_msg(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# === УРОВЕНЬ 2: УПРАВЛЕНИЕ ПОДРАЗДЕЛАМИ ===

@router.callback_query(AdminStates.subsection_management, F.data == "add_new_sub")
async def add_sub_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название нового подраздела:")
    await state.set_state(AdminStates.add_subsection)
    await callback.answer()

@router.message(AdminStates.add_subsection)
async def add_sub_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = message.text
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO subsections (section_id, name) VALUES (?, ?)", (data['current_section_id'], name))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Подраздел '{name}' добавлен.")
    await show_subsections_editor(message, data['current_section_id'], data['current_section_name'])
    await state.set_state(AdminStates.subsection_management)

@router.callback_query(AdminStates.subsection_management, F.data.startswith("manage_sub_"))
async def manage_subsection_options(callback: types.CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split("_")[2])
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM subsections WHERE id = ?", (sub_id,))
    sub_name = cursor.fetchone()[0]
    conn.close()
    
    await state.update_data(current_sub_id=sub_id, current_sub_name=sub_name)
    
    text = f"📂 **{sub_name}**"
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT section_id FROM subsections WHERE id = ?", (sub_id,))
    section_id = cursor.fetchone()[0]
    conn.close()
    kb = _subsection_menu_kb(sub_id, section_id)
    kb[-1] = [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subs_list")]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(AdminStates.subsection_management, F.data == "back_to_subs_list")
async def back_to_subs_list(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.delete() # Удаляем старое меню
    await show_subsections_editor(callback.message, data['current_section_id'], data['current_section_name'])

@router.callback_query(AdminStates.subsection_management, F.data == "delete_sub")
async def delete_subsection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sub_id = data['current_sub_id']
    
    conn = create_connection()
    cursor = conn.cursor()
    # Удаляем неисправности и шаги внутри
    cursor.execute("DELETE FROM subsections WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
    
    await callback.answer("Подраздел удален")
    await back_to_subs_list(callback, state)

@router.callback_query(AdminStates.subsection_management, F.data == "rename_sub")
async def rename_sub_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название:")
    await state.set_state(AdminStates.edit_subsection_name)
    await callback.answer()

@router.message(AdminStates.edit_subsection_name)
async def rename_sub_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_name = message.text
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE subsections SET name = ? WHERE id = ?", (new_name, data['current_sub_id']))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Переименовано.")
    await show_subsections_editor(message, data['current_section_id'], data['current_section_name'])
    await state.set_state(AdminStates.subsection_management)

