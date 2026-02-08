import sqlite3
from config import DATABASE_PATH

def migrate_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 1. Создаем таблицу подразделов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subsections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER,
        name TEXT NOT NULL,
        FOREIGN KEY (section_id) REFERENCES sections(id)
    );
    """)
    
    # 2. Добавляем колонку subsection_id в malfunctions, если нет
    try:
        cursor.execute("ALTER TABLE malfunctions ADD COLUMN subsection_id INTEGER")
    except:
        pass

    # 3. Создаем "Общий подраздел" для существующих записей, чтобы они не пропали
    cursor.execute("SELECT id FROM sections")
    sections = cursor.fetchall()
    
    for s_id in sections:
        # Проверяем, есть ли уже подразделы
        cursor.execute("SELECT id FROM subsections WHERE section_id = ?", (s_id[0],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO subsections (section_id, name) VALUES (?, ?)", (s_id[0], "Общее"))
            sub_id = cursor.lastrowid
            
            # Переносим старые неисправности в этот подраздел
            cursor.execute("UPDATE malfunctions SET subsection_id = ? WHERE section_id = ? AND subsection_id IS NULL", (sub_id, s_id[0]))
            
    conn.commit()
    conn.close()
    print("Миграция БД завершена.")

if __name__ == "__main__":
    migrate_db()
