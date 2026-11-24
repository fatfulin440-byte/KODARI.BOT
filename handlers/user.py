from pykodaribot import Router, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pykodaribot.filters import command, callback_data, callback_data_prefix

from config import bot
from services.loader import (
    load_catalog,
    search_topics,
    init_stats_table,
    init_mistakes_table,
    get_random_quiz,
    update_user_score,
    get_leaderboard,
    add_mistake,
    remove_mistake,
    get_mistakes_count,
    get_random_mistake_quiz,
    get_user_profile,
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
    mistake_options_keyboard,
)

router = Router()
init_stats_table()
init_mistakes_table()
CATALOG = load_catalog()


@router.message(command("start"))
async def cmd_start(message: Message):
    m_count = get_mistakes_count(message.from_user.id)
    await message.answer(
        text="📚 Школьный справочник для 9–11 классов.\n\n"
             "Выберите предмет из меню ниже или просто напишите слово для поиска (например: «дискриминант»):",
        reply_markup=subjects_keyboard(CATALOG, m_count),
    )


@router.callback_query(callback_data("noop"))
async def noop_callback(call: CallbackQuery):
    await call.answer()


@router.callback_query(callback_data("menu"))
async def go_main_menu(call: CallbackQuery):
    m_count = get_mistakes_count(call.from_user.id)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📚 Школьный справочник для 9–11 классов.\nВыберите предмет:",
        reply_markup=subjects_keyboard(CATALOG, m_count),
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
        was_mistake = remove_mistake(call.from_user.id, subj_key, grade_key, topic_key)
        extra = "\n🎉 Ошибка по этой теме закрыта!" if was_mistake else ""
        result_text = f"✅ Верно!\n\nПравильный ответ: {correct_text}{extra}"
    else:
        add_mistake(call.from_user.id, subj_key, grade_key, topic_key)
        chosen_text = quiz["options"][chosen_idx]
        result_text = (
            f"❌ Неверно. (Тема добавлена в «❌ Ошибки» для повторения)\n"
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
        was_mistake = remove_mistake(user.id, subj_key, grade_key, topic_key)
        extra = " (ошибка закрыта! 🎉)" if was_mistake else ""
        status_line = f"✅ **Верно!** (+1 балл){extra}\nПравильный ответ: {correct_text}"
    else:
        add_mistake(user.id, subj_key, grade_key, topic_key)
        chosen_text = quiz["options"][chosen_idx]
        status_line = (
            f"❌ **Неверно.** (Сохранено в «❌ Ошибки»)\n"
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


@router.callback_query(callback_data("mistakes:next"))
async def mistake_next_question(call: CallbackQuery):
    user_id = call.from_user.id
    q = get_random_mistake_quiz(user_id)

    if not q:
        m_count = get_mistakes_count(user_id)
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎉 **Отличная работа! У вас нет незакрытых ошибок.**\n\nВсе сложные темы отработаны. Можно переходить в тренажёр за новыми баллами!",
            reply_markup=subjects_keyboard(CATALOG, m_count),
        )
        await call.answer()
        return

    rem_count = get_mistakes_count(user_id)
    text = (
        f"❌ **Работа над ошибками** (осталось тем: {rem_count})\n"
        f"Предмет: {q['subj_title']} • {q['topic_title']}\n\n"
        f"❓ {q['question']}"
    )
    kb = mistake_options_keyboard(q["subject_key"], q["grade_key"], q["topic_key"], q["options"])

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=kb,
    )
    await call.answer()


@router.callback_query(callback_data_prefix("m_ans:"))
@router.callback_query(callback_data_prefix("m_ans:"))
async def mistake_check_answer(call: CallbackQuery):
    parts = call.data.split(":")
    parts.pop(0)
    subj_key = parts.pop(0)
    grade_key = parts.pop(0)
    topic_key = parts.pop(0)
    chosen_idx = int(parts.pop(0))

    topic = CATALOG[subj_key]["grades"][grade_key]["topics"][topic_key]
    quiz = topic["quiz"]
    correct_idx = quiz["correct"]
    correct_text = quiz["options"][correct_idx]
    user_id = call.from_user.id

    if chosen_idx == correct_idx:
        remove_mistake(user_id, subj_key, grade_key, topic_key)
        rem = get_mistakes_count(user_id)
        status_line = f"✅ **Верно! Ошибка закрыта.**\nПравильный ответ: {correct_text}\n\nОсталось отработать тем: **{rem}**"
    else:
        chosen_text = quiz["options"][chosen_idx]
        rem = get_mistakes_count(user_id)
        status_line = (
            f"❌ **Снова неверно.** Тема остаётся в списке ошибок.\n"
            f"Ваш ответ: {chosen_text}\n"
            f"✅ Правильный ответ: {correct_text}\n\nОсталось отработать тем: **{rem}**"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Следующая ошибка", callback_data="mistakes:next")],
        [InlineKeyboardButton(text="📖 Открыть шпаргалку по теме", callback_data=f"topic:{subj_key}:{grade_key}:{topic_key}")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu")],
    ])

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"❌ **Работа над ошибками** («{topic['title']}»)\n\n{status_line}",
        reply_markup=kb,
    )
    await call.answer()
