import sqlite3
from config import DATABASE_PATH

def clean_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("Очистка тестовых данных (подраздел 'Общее')...")
    
    # Находим ID подразделов с именем "Общее"
    cursor.execute("SELECT id FROM subsections WHERE name = 'Общее'")
    subs = cursor.fetchall()
    
    for sub in subs:
        sub_id = sub[0]
        # Удаляем шаги
        cursor.execute("DELETE FROM steps WHERE malfunction_id IN (SELECT id FROM malfunctions WHERE subsection_id = ?)", (sub_id,))
        # Удаляем неисправности
        cursor.execute("DELETE FROM malfunctions WHERE subsection_id = ?", (sub_id,))
        # Удаляем подраздел
        cursor.execute("DELETE FROM subsections WHERE id = ?", (sub_id,))
        
    conn.commit()
    conn.close()
    print("Готово. База очищена от тестовых данных.")

if __name__ == "__main__":
    clean_db()
