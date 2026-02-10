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
    add_section = State()  # ввод названия и кода нового раздела

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
            f"Нет доступа. Ваш Telegram ID: {message.from_user.id}\n\n"
            f"В .env на сервере добавьте строку:\n"
            f"ADMIN_IDS={message.from_user.id}"
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
        await message.answer("❌ Неверный пароль администратора.")
        await state.clear()

async def show_main_admin_menu(message: types.Message):
    sections = get_all_sections()
    kb = []
    for name, code in sections:
        kb.append([KeyboardButton(text=f"{code}. {name}")])
    kb.append([KeyboardButton(text="➕ ДОБАВИТЬ РАЗДЕЛ")])
    kb.append([KeyboardButton(text="🔙 ВЫЙТИ ИЗ АДМИНКИ")])
    
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Меню:", reply_markup=keyboard)

@router.message(AdminStates.section_selection, F.text == "➕ ДОБАВИТЬ РАЗДЕЛ")
async def add_section_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название раздела:")
    await state.set_state(AdminStates.add_section)

@router.message(AdminStates.add_section, F.text)
async def add_section_finish(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не должно быть пустым.")
        return
    conn = create_connection()
    if not conn:
        await message.answer("Ошибка БД.")
        await state.set_state(AdminStates.section_selection)
        return
    cursor = conn.cursor()
    # Автоматически подбираем следующий свободный код (по аналогии 4.1, 4.2, 4.3 -> 4.4 и т.д.)
    cursor.execute("SELECT code FROM sections")
    rows = cursor.fetchall()
    next_code = "4.1"
    nums = []
    for (c,) in rows:
        parts = str(c).split(".")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            nums.append((int(parts[0]), int(parts[1])))
    if nums:
        nums.sort()
        major, minor = nums[-1]
        major_new, minor_new = major, minor + 1
        candidate = f"{major_new}.{minor_new}"
        # вдруг такой код уже есть (на всякий случай крутим дальше)
        existing = {c for (c,) in rows}
        while candidate in existing:
            minor_new += 1
            candidate = f"{major_new}.{minor_new}"
        next_code = candidate
    cursor.execute("INSERT INTO sections (name, code) VALUES (?, ?)", (name, next_code))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Раздел «{name}» (код {next_code}) добавлен. Он появился в меню.")
    await state.set_state(AdminStates.section_selection)
    await show_main_admin_menu(message)

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
    cursor.execute("SELECT id, name, code FROM sections WHERE code LIKE ?", (f"{code}%",))
    res = cursor.fetchone()
    conn.close()
    if not res:
        await message.answer("Раздел не найден.")
        return True
    section_id, section_name, section_code = res[0], res[1], str(res[2])
    await state.update_data(current_section_id=section_id, current_section_name=section_name)
    # По аналогии с подразделами: сначала экран выбора действия (Подразделы / Удалить раздел для добавленных)
    can_delete = section_code not in ("4.1", "4.2", "4.3")
    kb = [[InlineKeyboardButton(text="📂 Подразделы", callback_data=f"open_subs_{section_id}")]]
    if can_delete:
        kb.append([InlineKeyboardButton(text="🗑 Удалить раздел", callback_data=f"delete_section_{section_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="close_admin_msg")])
    await message.answer(
        f"**{section_name}**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.section_selection)  # остаёмся в выборе раздела, подразделы откроются по callback
    return True

@router.message(AdminStates.section_selection)
async def process_section_click(message: types.Message, state: FSMContext):
    await _do_section_click(message, state, message.text)

# Запасной обработчик: админ нажал раздел (4.1., 4.2., 4.4. и т.д.), но state потерялся
@router.message(~StateFilter(AdminStates.section_selection), F.text.regexp(r"^\d+\.\d+\."))
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
    # Кнопка Назад (без "УДАЛИТЬ РАЗДЕЛ" здесь — удаление в предыдущем шаге по аналогии)
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="close_admin_msg")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "close_admin_msg")
async def close_admin_msg(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("open_subs_"))
async def open_subsections(callback: types.CallbackQuery, state: FSMContext):
    """Открыть список подразделов раздела (кнопка «Подразделы» на промежуточном экране)."""
    section_id = int(callback.data.split("_")[2])
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    section_name = row[0]
    await state.update_data(current_section_id=section_id, current_section_name=section_name)
    await state.set_state(AdminStates.subsection_management)
    # Показать список подразделов в том же сообщении
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM subsections WHERE section_id = ?", (section_id,))
    subs = cursor.fetchall()
    conn.close()
    text = f"**{section_name}**"
    kb = [[InlineKeyboardButton(text=f"📂 {name}", callback_data=f"manage_sub_{s_id}")] for s_id, name in subs]
    kb.append([InlineKeyboardButton(text="➕ ДОБАВИТЬ ПОДРАЗДЕЛ", callback_data="add_new_sub")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="close_admin_msg")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
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

@router.callback_query(F.data.startswith("delete_section_"))
async def delete_section(callback: types.CallbackQuery, state: FSMContext):
    """Удаление раздела, созданного админом (кроме 4.1, 4.2, 4.3)."""
    section_id = int(callback.data.split("_")[2])

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name FROM sections WHERE id = ?", (section_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await callback.answer("Раздел не найден", show_alert=True)
        return
    code, name = str(row[0]), row[1]
    if code in ("4.1", "4.2", "4.3"):
        conn.close()
        await callback.answer("Этот раздел удалять нельзя", show_alert=True)
        return

    # Удаляем всё, что подвязано к разделу (subsections, malfunctions, steps)
    cursor.execute("SELECT id FROM subsections WHERE section_id = ?", (section_id,))
    sub_ids = [r[0] for r in cursor.fetchall()]
    if sub_ids:
        q_marks = ",".join(["?"] * len(sub_ids))
        cursor.execute(f"DELETE FROM steps WHERE malfunction_id IN (SELECT id FROM malfunctions WHERE subsection_id IN ({q_marks}))", sub_ids)
        cursor.execute(f"DELETE FROM malfunctions WHERE subsection_id IN ({q_marks})", sub_ids)
        cursor.execute("DELETE FROM subsections WHERE section_id = ?", (section_id,))
    # На всякий случай удалим и по section_id
    cursor.execute("DELETE FROM malfunctions WHERE section_id = ?", (section_id,))
    cursor.execute("DELETE FROM sections WHERE id = ?", (section_id,))
    conn.commit()
    conn.close()

    await callback.answer(f"Раздел «{name}» удалён", show_alert=True)
    await callback.message.delete()
    await state.set_state(AdminStates.section_selection)
    await show_main_admin_menu(callback.message)

async def _show_subsection_menu(callback: types.CallbackQuery, state: FSMContext, sub_id: int):
    """Показать меню подраздела (редактировать/переименовать/удалить)."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, section_id FROM subsections WHERE id = ?", (sub_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await callback.answer("Подраздел не найден", show_alert=True)
        return
    sub_name, section_id = row[0], row[1]
    cursor.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
    section_name = cursor.fetchone()[0]
    conn.close()
    await state.update_data(current_sub_id=sub_id, current_sub_name=sub_name, current_section_id=section_id, current_section_name=section_name)
    await state.set_state(AdminStates.subsection_management)
    text = f"📂 **{sub_name}**"
    kb = _subsection_menu_kb(sub_id, section_id)
    kb[-1] = [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subs_list")]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("manage_sub_"))
async def manage_subsection_options(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    sub_id = int(callback.data.split("_")[2])
    await _show_subsection_menu(callback, state, sub_id)
    await callback.answer()

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

