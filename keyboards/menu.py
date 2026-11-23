from pykodaribot import InlineKeyboardMarkup, InlineKeyboardButton

TOPICS_PER_PAGE = 5  # Сколько тем показывать на одной странице


def subjects_keyboard(catalog: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=subj["title"], callback_data=f"subj:{key}")]
        for key, subj in catalog.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grades_keyboard(subject_key: str, subject_data: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=grade["title"], callback_data=f"grade:{subject_key}:{g_key}:0")]
        for g_key, grade in subject_data["grades"].items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ К предметам", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topics_keyboard(subject_key: str, grade_key: str, grade_data: dict, page: int = 0) -> InlineKeyboardMarkup:
    all_topics = list(grade_data["topics"].items())
    total_pages = (len(all_topics) + TOPICS_PER_PAGE - 1) // TOPICS_PER_PAGE

    start = page * TOPICS_PER_PAGE
    end = start + TOPICS_PER_PAGE
    page_topics = all_topics[start:end]

    buttons = [
        [InlineKeyboardButton(text=topic["title"], callback_data=f"topic:{subject_key}:{grade_key}:{t_key}")]
        for t_key, topic in page_topics
    ]

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"grade:{subject_key}:{grade_key}:{page - 1}"))
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"grade:{subject_key}:{grade_key}:{page + 1}"))
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к классам", callback_data=f"subj:{subject_key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_topics_keyboard(
    subject_key: str,
    grade_key: str,
    topic_key: str | None = None,
    has_quiz: bool = False,
) -> InlineKeyboardMarkup:
    buttons = []
    if has_quiz and topic_key:
        buttons.append([
            InlineKeyboardButton(
                text="📝 Пройти тест по теме",
                callback_data=f"quiz:{subject_key}:{grade_key}:{topic_key}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к темам", callback_data=f"grade:{subject_key}:{grade_key}:0")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quiz_options_keyboard(
    subject_key: str,
    grade_key: str,
    topic_key: str,
    options: list[str],
) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"ans:{subject_key}:{grade_key}:{topic_key}:{idx}")]
        for idx, opt in enumerate(options)
    ]
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Вернуться к теории",
            callback_data=f"topic:{subject_key}:{grade_key}:{topic_key}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_results_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=item["title"], callback_data=item["callback_data"])]
        for item in results[:5]
    ]
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
