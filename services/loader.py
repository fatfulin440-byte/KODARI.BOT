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
def init_stats_table():
    """Создаёт таблицу статистики и рейтинга учеников."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            correct_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_random_quiz(subject_key: str | None = None) -> dict | None:
    """Выбирает случайный тестовый вопрос (по всем предметам или по конкретному)."""
    conn = get_connection()
    cur = conn.cursor()

    if subject_key and subject_key != "all":
        cur.execute("""
            SELECT 
                t.subject_key, t.grade_key, t.topic_key, t.title AS topic_title,
                s.title AS subj_title,
                q.question, q.options_json, q.correct_idx
            FROM quizzes q
            JOIN topics t ON t.id = q.topic_id
            JOIN subjects s ON s.key = t.subject_key
            WHERE t.subject_key = ?
            ORDER BY RANDOM()
            LIMIT 1
        """, (subject_key,))
    else:
        cur.execute("""
            SELECT 
                t.subject_key, t.grade_key, t.topic_key, t.title AS topic_title,
                s.title AS subj_title,
                q.question, q.options_json, q.correct_idx
            FROM quizzes q
            JOIN topics t ON t.id = q.topic_id
            JOIN subjects s ON s.key = t.subject_key
            ORDER BY RANDOM()
            LIMIT 1
        """)

    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "subject_key": row["subject_key"],
        "grade_key": row["grade_key"],
        "topic_key": row["topic_key"],
        "topic_title": row["topic_title"],
        "subj_title": row["subj_title"],
        "question": row["question"],
        "options": json.loads(row["options_json"]),
        "correct": row["correct_idx"],
    }



def update_user_score(user_id: int, full_name: str, is_correct: bool) -> dict:
    """Обновляет статистику ученика в SQLite и возвращает актуальные показатели."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT correct_count, total_count, streak, best_streak FROM user_stats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if row:
        correct = row["correct_count"] + (1 if is_correct else 0)
        total = row["total_count"] + 1
        streak = (row["streak"] + 1) if is_correct else 0
        best_streak = max(row["best_streak"], streak)
        cur.execute(
            """
            UPDATE user_stats
            SET full_name = ?, correct_count = ?, total_count = ?, streak = ?, best_streak = ?
            WHERE user_id = ?
            """,
            (full_name, correct, total, streak, best_streak, user_id),
        )
    else:
        correct = 1 if is_correct else 0
        total = 1
        streak = 1 if is_correct else 0
        best_streak = streak
        cur.execute(
            """
            INSERT INTO user_stats (user_id, full_name, correct_count, total_count, streak, best_streak)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name, correct, total, streak, best_streak),
        )

    conn.commit()
    conn.close()
    return {"correct": correct, "total": total, "streak": streak, "best_streak": best_streak}


def get_leaderboard(limit: int = 10) -> list[dict]:
    """Возвращает топ учеников по количеству правильных ответов."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT full_name, correct_count, total_count, best_streak
        FROM user_stats
        WHERE correct_count > 0
        ORDER BY correct_count DESC, best_streak DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
def init_mistakes_table():
    """Создаёт таблицу для хранения ошибок учеников."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_key TEXT NOT NULL,
            grade_key TEXT NOT NULL,
            topic_key TEXT NOT NULL,
            UNIQUE(user_id, subject_key, grade_key, topic_key)
        )
    """)
    conn.commit()
    conn.close()


def add_mistake(user_id: int, subject_key: str, grade_key: str, topic_key: str):
    """Записывает тему в список ошибок ученика (если её там ещё нет)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO user_mistakes (user_id, subject_key, grade_key, topic_key)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, subject_key, grade_key, topic_key),
    )
    conn.commit()
    conn.close()


def remove_mistake(user_id: int, subject_key: str, grade_key: str, topic_key: str) -> bool:
    """Удаляет тему из списка ошибок после правильного ответа. Возвращает True, если ошибка была закрыта."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM user_mistakes
        WHERE user_id = ? AND subject_key = ? AND grade_key = ? AND topic_key = ?
        """,
        (user_id, subject_key, grade_key, topic_key),
    )
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_mistakes_count(user_id: int) -> int:
    """Возвращает количество незакрытых ошибок пользователя."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM user_mistakes WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_random_mistake_quiz(user_id: int) -> dict | None:
    """Выбирает случайный вопрос из списка ошибок ученика."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            m.subject_key, m.grade_key, m.topic_key,
            t.title AS topic_title, s.title AS subj_title,
            q.question, q.options_json, q.correct_idx
        FROM user_mistakes m
        JOIN topics t ON t.subject_key = m.subject_key AND t.grade_key = m.grade_key AND t.topic_key = m.topic_key
        JOIN subjects s ON s.key = m.subject_key
        JOIN quizzes q ON q.topic_id = t.id
        WHERE m.user_id = ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "subject_key": row["subject_key"],
        "grade_key": row["grade_key"],
        "topic_key": row["topic_key"],
        "topic_title": row["topic_title"],
        "subj_title": row["subj_title"],
        "question": row["question"],
        "options": json.loads(row["options_json"]),
        "correct": row["correct_idx"],
    }
