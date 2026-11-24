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
    trainer_filter_keyboard,
    trainer_options_keyboard,
    trainer_after_answer_keyboard,
)

router = Router()
init_stats_table()
CATALOG = load_catalog()


@router.message(command("start"))
async def cmd_start(message: Message):
    await message.answer(
        text="📚 Школьный справочник для 9–11 классов.\n\n"
             "Выберите предмет из меню ниже или просто напишите слово для поиска (например: «дискриминант»):",
        reply_markup=subjects_keyboard(CATALOG),
    )


@router.callback_query(callback_data("noop"))
async def noop_callback(call: CallbackQuery):
    await call.answer()


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
    parts.pop(0)
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


# --- БЛОК ТРЕНАЖЁРА С ФИЛЬТРОМ ПО ПРЕДМЕТАМ ---

@router.callback_query(callback_data("trainer_menu"))
async def show_trainer_menu(call: CallbackQuery):
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎯 **Настройка тренажёра**\n\nВыберите предмет для тренировки или запустите общий микс по всем темам:",
        reply_markup=trainer_filter_keyboard(CATALOG),
    )
    await call.answer()


@router.callback_query(callback_data_prefix("trainer:"))
async def trainer_next_question(call: CallbackQuery):
    _, filter_key = call.data.split(":")
    q = get_random_quiz(filter_key)

    if not q:
        await call.answer("По этому предмету пока нет тестовых вопросов.", show_alert=True)
        return

    mode_label = "Все предметы" if filter_key == "all" else q["subj_title"]
    text = (
        f"🎯 **Тренажёр** ({mode_label})\n"
        f"Предмет: {q['subj_title']}\n\n"
        f"❓ {q['question']}"
    )
    kb = trainer_options_keyboard(filter_key, q["subject_key"], q["grade_key"], q["topic_key"], q["options"])

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=kb,
    )
    await call.answer()


@router.callback_query(callback_data_prefix("tr_ans:"))
async def trainer_check_answer(call: CallbackQuery):
    parts = call.data.split(":")
    parts.pop(0)
    filter_key = parts.pop(0)
    subj_key = parts.pop(0)
    grade_key = parts.pop(0)
    topic_key = parts.pop(0)
    chosen_idx = int(parts.pop(0))

    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    quiz = topic["quiz"]
    correct_idx = quiz["correct"]
    correct_text = quiz["options"][correct_idx]
    is_correct = (chosen_idx == correct_idx)

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
        reply_markup=trainer_after_answer_keyboard(filter_key, subj_key, grade_key, topic_key),
    )
    await call.answer()


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
        [InlineKeyboardButton(text="🎯 В тренажёр", callback_data="trainer_menu")],
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
