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
