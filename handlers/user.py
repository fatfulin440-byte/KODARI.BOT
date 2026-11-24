from pykodaribot import Router, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pykodaribot.filters import command, callback_data, callback_data_prefix
from config import bot
from services.loader import (
    load_catalog,
    search_topics,
    init_stats_table,
    get_random_quiz,
    update_user_score,
    get_leaderboard,
)
from keyboards.menu import (
    subjects_keyboard,
    grades_keyboard,
    topics_keyboard,
    back_to_topics_keyboard,
    quiz_options_keyboard,
    search_results_keyboard,
    trainer_options_keyboard,
    trainer_after_answer_keyboard,
)

router = Router()
init_stats_table()
CATALOG = load_catalog()

from pykodaribot import Router, Message, CallbackQuery
from pykodaribot.filters import command, callback_data, callback_data_prefix

from config import bot
from services.loader import load_catalog, search_topics
from keyboards.menu import (
    subjects_keyboard,
    grades_keyboard,
    topics_keyboard,
    back_to_topics_keyboard,
    quiz_options_keyboard,
    search_results_keyboard,
)

router = Router()
CATALOG = load_catalog()


@router.message(command("start"))
async def cmd_start(message: Message):
    await message.answer(
        text="📚 Школьный справочник для 9–11 классов.\n\n"
             "Выберите предмет из меню ниже или просто напишите слово для поиска (например: «дискриминант»):",
        reply_markup=subjects_keyboard(CATALOG),
    )


@router.callback_query(callback_data("menu"))
async def go_main_menu(call: CallbackQuery):
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📚 Школьный справочник для 9–11 классов.\nВыберите предмет:",
        reply_markup=subjects_keyboard(CATALOG),
    )
    await call.answer()


@router.callback_query(callback_data_prefix("subj:"))
async def select_subject(call: CallbackQuery):
    _, subj_key = call.data.split(":")
    subject = CATALOG[subj_key]

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{subject['title']}\nВыберите класс:",
        reply_markup=grades_keyboard(subj_key, subject),
    )
    await call.answer()


@router.callback_query(callback_data_prefix("grade:"))
async def select_grade(call: CallbackQuery):
    parts = call.data.split(":")
    parts.pop(0)  # убираем слово "grade"
    subj_key = parts.pop(0)
    grade_key = parts.pop(0)
    page = int(parts.pop(0)) if parts else 0

    grade = CATALOG[subj_key]["grades"][grade_key]

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{grade['title']}\nВыберите тему:",
        reply_markup=topics_keyboard(subj_key, grade_key, grade, page),
    )
    await call.answer()




@router.callback_query(callback_data_prefix("topic:"))
async def show_topic(call: CallbackQuery):
    _, subj_key, grade_key, topic_key = call.data.split(":")
    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    has_quiz = "quiz" in topic

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📌 {topic['title']}\n\n{topic['text']}",
        reply_markup=back_to_topics_keyboard(subj_key, grade_key, topic_key, has_quiz),
    )
    await call.answer()


# Запуск теста по выбранной теме (quiz:math:9:quad)
@router.callback_query(callback_data_prefix("quiz:"))
async def start_quiz(call: CallbackQuery):
    _, subj_key, grade_key, topic_key = call.data.split(":")
    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    quiz = topic["quiz"]

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📝 Тест по теме «{topic['title']}»\n\n❓ {quiz['question']}",
        reply_markup=quiz_options_keyboard(subj_key, grade_key, topic_key, quiz["options"]),
    )
    await call.answer()


# Проверка ответа пользователя (ans:math:9:quad:2)
@router.callback_query(callback_data_prefix("ans:"))
async def check_quiz_answer(call: CallbackQuery):
    _, subj_key, grade_key, topic_key, chosen_str = call.data.split(":")
    chosen_idx = int(chosen_str)

    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    quiz = topic["quiz"]
    correct_idx = quiz["correct"]
    correct_text = quiz["options"][correct_idx]

    if chosen_idx == correct_idx:
        result_text = f"✅ Верно!\n\nПравильный ответ: {correct_text}"
    else:
        chosen_text = quiz["options"][chosen_idx]
        result_text = (
            f"❌ Неверно.\n"
            f"Ваш ответ: {chosen_text}\n"
            f"✅ Правильный ответ: {correct_text}"
        )

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📝 Тест: «{topic['title']}»\n\n{result_text}",
        reply_markup=back_to_topics_keyboard(subj_key, grade_key, topic_key, has_quiz=True),
    )
    await call.answer()

# Запуск / следующий случайный вопрос тренажёра
@router.callback_query(callback_data("trainer:next"))
async def trainer_next_question(call: CallbackQuery):
    q = get_random_quiz()
    if not q:
        await call.answer("В базе пока нет тестовых вопросов.", show_alert=True)
        return

    text = (
        f"🎯 **Тренажёр ЕГЭ/ОГЭ**\n"
        f"Предмет: {q['subj_title']}\n\n"
        f"❓ {q['question']}"
    )
    kb = trainer_options_keyboard(q["subject_key"], q["grade_key"], q["topic_key"], q["options"])

    try:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=kb,
        )
    except Exception:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        await bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=kb)
    await call.answer()


# Проверка ответа в тренажёре и обновление рейтинга
@router.callback_query(callback_data_prefix("tr_ans:"))
async def trainer_check_answer(call: CallbackQuery):
    parts = call.data.split(":")
    parts.pop(0)  # "tr_ans"
    subj_key = parts.pop(0)
    grade_key = parts.pop(0)
    topic_key = parts.pop(0)
    chosen_idx = int(parts.pop(0))

    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    quiz = topic["quiz"]
    correct_idx = quiz["correct"]
    correct_text = quiz["options"][correct_idx]
    is_correct = (chosen_idx == correct_idx)

    # Формируем имя пользователя для таблицы лидеров
    user = call.from_user
    display_name = getattr(user, "first_name", None) or getattr(user, "username", None) or f"Ученик #{user.id}"

    stats = update_user_score(user.id, display_name, is_correct)

    if is_correct:
        status_line = f"✅ **Верно!** (+1 балл)\nПравильный ответ: {correct_text}"
    else:
        chosen_text = quiz["options"][chosen_idx]
        status_line = (
            f"❌ **Неверно.**\n"
            f"Ваш ответ: {chosen_text}\n"
            f"✅ Правильный ответ: {correct_text}"
        )

    result_text = (
        f"🎯 **Результат раунда** (тема: «{topic['title']}»)\n\n"
        f"{status_line}\n\n"
        f"📊 Ваш счёт: **{stats['correct']}** из {stats['total']}  |  🔥 Серия: **{stats['streak']}** (рекорд: {stats['best_streak']})"
    )

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=result_text,
        reply_markup=trainer_after_answer_keyboard(subj_key, grade_key, topic_key),
    )
    await call.answer()


# Таблица лидеров
@router.callback_query(callback_data("leaderboard"))
async def show_leaderboard(call: CallbackQuery):
    leaders = get_leaderboard(10)
    if not leaders:
        text = "🏆 **Таблица лидеров пока пуста.**\n\nНажмите «🎯 Тренажёр» и ответьте на первый вопрос, чтобы занять 1-е место!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 **Топ-10 знатоков ЕГЭ/ОГЭ:**\n"]
        for idx, row in enumerate(leaders):
            prefix = medals[idx] if idx < 3 else f"{idx + 1}."
            lines.append(
                f"{prefix} **{row['full_name']}** — {row['correct_count']} б. (серия: {row['best_streak']} 🔥)"
            )
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 В тренажёр", callback_data="trainer:next")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")],
    ])

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=kb,
    )
    await call.answer()

@router.message()
async def handle_search(message: Message):
    if not message.text or message.text.startswith("/"):
        return

    results = search_topics(CATALOG, message.text)
    if not results:
        await message.answer(
            text=f"По запросу «{message.text}» ничего не найдено. Попробуйте другое слово или откройте меню:",
            reply_markup=subjects_keyboard(CATALOG),
        )
        return

    await message.answer(
        text=f"🔍 Найдено тем по запросу «{message.text}» ({len(results)}):",
        reply_markup=search_results_keyboard(results),
    )
