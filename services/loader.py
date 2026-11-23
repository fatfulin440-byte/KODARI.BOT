import os
import json

# Определяем точный путь к папке проекта (где лежит main.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_catalog() -> dict:
    catalog = {}
    if not os.path.exists(DATA_DIR):
        print(f"ВНИМАНИЕ: Папка {DATA_DIR} не найдена!")
        return catalog

    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.endswith(".json"):
            subject_key = filename[:-5]
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    catalog[subject_key] = json.load(f)
                print(f"Успешно загружен предмет: {filename}")
            except Exception as e:
                print(f"ОШИБКА в файле {filename}: {e}")
    return catalog


def search_topics(catalog: dict, query: str) -> list[dict]:
    """Ищет совпадения в названиях и текстах всех тем."""
    query = query.strip().lower()
    if len(query) < 2:
        return []

    results = []
    for subj_key, subj in catalog.items():
        for grade_key, grade in subj["grades"].items():
            for topic_key, topic in grade["topics"].items():
                if query in topic["title"].lower() or query in topic["text"].lower():
                    results.append({
                        "title": f"{subj['title']} • {topic['title']}",
                        "callback_data": f"topic:{subj_key}:{grade_key}:{topic_key}"
                    })
    return results
