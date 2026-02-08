"""Поиск по подразделам (название и текст)."""
from database import create_connection
from config import SEARCH_LIMIT


def search_subsections(query: str):
    """Поиск по названиям подразделов (без учёта регистра)."""
    conn = create_connection()
    results = []
    if conn:
        try:
            cursor = conn.cursor()
            q = query.strip()
            if not q:
                return results
            # Без учёта регистра (LOWER для кириллицы)
            cursor.execute("""
                SELECT sub.id, sub.name, s.name
                FROM subsections sub
                JOIN sections s ON sub.section_id = s.id
                WHERE LOWER(sub.name) LIKE '%' || LOWER(?) || '%'
                ORDER BY s.code, sub.name
                LIMIT ?
            """, (q, SEARCH_LIMIT))
            results = cursor.fetchall()
        except Exception as e:
            print(f"Ошибка поиска: {e}")
        finally:
            conn.close()
    return results


def get_subsection_content(subsection_id: int):
    """Получить название и текст подраздела по ID."""
    conn = create_connection()
    row = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, content FROM subsections WHERE id = ?",
                (subsection_id,)
            )
            row = cursor.fetchone()
        finally:
            conn.close()
    return row
