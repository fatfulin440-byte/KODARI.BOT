import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "database", "handbook.db")


def init_and_migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Создаём таблицы реляционной базы данных
    cur.executescript("""
        DROP TABLE IF EXISTS quizzes;
        DROP TABLE IF EXISTS topics;
        DROP TABLE IF EXISTS subjects;

        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL
        );

        CREATE TABLE topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_key TEXT NOT NULL,
            grade_key TEXT NOT NULL,
            grade_title TEXT NOT NULL,
            topic_key TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            UNIQUE(subject_key, grade_key, topic_key)
        );

        CREATE TABLE quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_idx INTEGER NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
        );
    """)

    total_topics = 0

    # 2. Переносим все JSON-файлы из папки data в таблицы SQLite
    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue

        subj_key = filename[:-5]
        filepath = os.path.join(DATA_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            subj_data = json.load(f)

        cur.execute(
            "INSERT INTO subjects (key, title) VALUES (?, ?)",
            (subj_key, subj_data["title"])
        )

        for grade_key, grade_data in subj_data["grades"].items():
            grade_title = grade_data["title"]
            for topic_key, topic_data in grade_data["topics"].items():
                cur.execute(
                    """
                    INSERT INTO topics (subject_key, grade_key, grade_title, topic_key, title, text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (subj_key, grade_key, grade_title, topic_key, topic_data["title"], topic_data["text"])
                )
                topic_id = cur.lastrowid
                total_topics += 1

                if "quiz" in topic_data:
                    q = topic_data["quiz"]
                    cur.execute(
                        """
                        INSERT INTO quizzes (topic_id, question, options_json, correct_idx)
                        VALUES (?, ?, ?, ?)
                        """,
                        (topic_id, q["question"], json.dumps(q["options"], ensure_ascii=False), q["correct"])
                    )

        print(f"Перенесён в БД: {subj_data['title']} ({filename})")

    conn.commit()
    conn.close()
    print(f"\nГотово! База данных создана: {DB_PATH}. Всего тем в БД: {total_topics}.")


if __name__ == "__main__":
    init_and_migrate()
