import sqlite3
from config import DATABASE_PATH

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
    except Exception as e:
        print(e)
    return conn

def create_tables():
    conn = create_connection()
    if conn is not None:
        cursor = conn.cursor()
        
        # Только три раздела
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL
        );
        """)

        # Подразделы (content — текст, который отображается в пункте)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subsections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            name TEXT NOT NULL,
            content TEXT,
            FOREIGN KEY (section_id) REFERENCES sections(id)
        );
        """)
        try:
            cursor.execute("ALTER TABLE subsections ADD COLUMN content TEXT")
        except:
            pass

        # Неисправности (оставляем таблицы для совместимости, не используем в новой логике)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS malfunctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            title TEXT NOT NULL,
            code TEXT,
            page INTEGER,
            FOREIGN KEY (section_id) REFERENCES sections(id)
        );
        """)

        # Миграция
        try:
            cursor.execute("ALTER TABLE malfunctions ADD COLUMN subsection_id INTEGER REFERENCES subsections(id)")
        except:
            pass 

        # Шаги решения
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            malfunction_id INTEGER,
            step_number INTEGER,
            description TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (malfunction_id) REFERENCES malfunctions(id)
        );
        """)

        # Предложения пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            problem_text TEXT,
            section_name TEXT,
            contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Заполняем базовые разделы
        cursor.execute("SELECT count(*) FROM sections")
        if cursor.fetchone()[0] == 0:
            sections = [
                ("Электрооборудование", "4.1"),
                ("Приборное оборудование", "4.2"),
                ("Радиоэлектронное оборудование", "4.3")
            ]
            cursor.executemany("INSERT INTO sections (name, code) VALUES (?, ?)", sections)

        # Миграция в подраздел "Общее"
        cursor.execute("SELECT id FROM sections")
        sections_list = cursor.fetchall()
        for s_id in sections_list:
             cursor.execute("SELECT count(*) FROM malfunctions WHERE section_id = ? AND (subsection_id IS NULL)", (s_id[0],))
             if cursor.fetchone()[0] > 0:
                 cursor.execute("SELECT id FROM subsections WHERE section_id = ? AND name = 'Общее'", (s_id[0],))
                 sub = cursor.fetchone()
                 if not sub:
                     cursor.execute("INSERT INTO subsections (section_id, name) VALUES (?, ?)", (s_id[0], "Общее"))
                     sub_id = cursor.lastrowid
                 else:
                     sub_id = sub[0]
                 
                 cursor.execute("UPDATE malfunctions SET subsection_id = ? WHERE section_id = ? AND subsection_id IS NULL", (sub_id, s_id[0]))

        conn.commit()
        conn.close()
    else:
        print("Ошибка подключения к БД")

def get_all_sections():
    conn = create_connection()
    sections = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, code FROM sections ORDER BY code")
            sections = cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения разделов: {e}")
        finally:
            conn.close()
    return sections

if __name__ == '__main__':
    create_tables()
