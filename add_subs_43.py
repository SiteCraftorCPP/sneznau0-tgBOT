# Подразделы 4.3 Радиоэлектронное оборудование
import sqlite3
from config import DATABASE_PATH

SUBS_43 = [
    "Невозможность ведения УКВ радиосвязи (УКВ радиостанции исправны)",
    "Мала дальность двухсторонней радиосвязи по радиостанции \"Баклан-20\"",
    "Неисправна РЛС \"Гроза - 26\"",
    "Неустойчивые показания УВ-5 радиовысотомера РВ-5",
    "Радиовысотомер РВ-4 не отрабатывает контрольную высоту в режиме \"Контроль\"",
    "Отсутствует (искажена) информация ответчика СОМ-64",
    "Не работает курсовой канал ОСЬ-1",
    "Не работает глиссадный канал ОСЬ-1",
    "По сообщению наземных служб не работает изделие \"020\"",
    "Ошибка в показаниях АРК-11 превышает допустимые значения",
    "Радиокомпас АРК-УД не работает в режиме автоматического пеленгования",
    "Не работает канал азимута РСБН-2С",
    "Не работает канал дальности РСБН-2С",
    "Неисправна радиостанция \"Микрон\"",
]

def main():
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM sections WHERE code = ?", ("4.3",))
    row = cur.fetchone()
    if not row:
        print("Раздел 4.3 не найден.")
        conn.close()
        return
    section_id = row[0]
    added = 0
    for name in SUBS_43:
        cur.execute("SELECT id FROM subsections WHERE section_id = ? AND name = ?", (section_id, name))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO subsections (section_id, name) VALUES (?, ?)", (section_id, name))
            added += 1
    conn.commit()
    conn.close()
    print(f"Добавлено подразделов в 4.3: {added}")

if __name__ == "__main__":
    main()
