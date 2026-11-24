import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "handbook.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_catalog() -> dict:
    """Загружает весь каталог предметов, тем и тестов из базы данных SQLite."""
    catalog = {}
    if not os.path.exists(DB_PATH):
        print(f"ВНИМАНИЕ: База данных {DB_PATH} не найдена! Запустите database/migrate.py")
        return catalog

    conn = get_connection()
    cur = conn.cursor()

    # Загружаем предметы
    cur.execute("SELECT key, title FROM subjects ORDER BY id")
    for subj in cur.fetchall():
        catalog[subj["key"]] = {
            "title": subj["title"],
            "grades": {}
        }

    # Загружаем темы и привязанные к ним тесты через LEFT JOIN
    cur.execute("""
        SELECT 
            t.subject_key, t.grade_key, t.grade_title,
            t.topic_key, t.title, t.text,
            q.question, q.options_json, q.correct_idx
        FROM topics t
        LEFT JOIN quizzes q ON q.topic_id = t.id
        ORDER BY t.id
    """)

    for row in cur.fetchall():
        s_key = row["subject_key"]
        g_key = row["grade_key"]
        t_key = row["topic_key"]

        if g_key not in catalog[s_key]["grades"]:
            catalog[s_key]["grades"][g_key] = {
                "title": row["grade_title"],
                "topics": {}
            }

        topic_entry = {
            "title": row["title"],
            "text": row["text"]
        }

        if row["question"]:
            topic_entry["quiz"] = {
                "question": row["question"],
                "options": json.loads(row["options_json"]),
                "correct": row["correct_idx"]
            }

        catalog[s_key]["grades"][g_key]["topics"][t_key] = topic_entry

    conn.close()
    print(f"Каталог успешно загружен из SQLite ({len(catalog)} предмета).")
    return catalog


def search_topics(catalog: dict, query: str) -> list[dict]:
    """Ищет темы через SQL-запрос к базе данных (без учёта регистра)."""
    query = query.strip().lower()
    if len(query) < 2 or not os.path.exists(DB_PATH):
        return []

    conn = get_connection()
    cur = conn.cursor()

    # SQLite LOWER() для кириллицы работает не всегда, поэтому фильтруем в Python по выборке из БД
    cur.execute("""
        SELECT t.subject_key, t.grade_key, t.topic_key, t.title, t.text, s.title AS subj_title
        FROM topics t
        JOIN subjects s ON s.key = t.subject_key
    """)

    results = []
    for row in cur.fetchall():
        if query in row["title"].lower() or query in row["text"].lower():
            results.append({
                "title": f"{row['subj_title']} • {row['title']}",
                "callback_data": f"topic:{row['subject_key']}:{row['grade_key']}:{row['topic_key']}"
            })

    conn.close()
    return results
