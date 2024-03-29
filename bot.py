import telebot
from telebot import types
from config import *
import gpt
import logging
import database as db

logging.basicConfig(filename="logs.txt", encoding="utf-8", level=logging.DEBUG, filemode="w",
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def add_buttons(buttons):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons)
    return keyboard


@bot.message_handler(commands=["new_story"])
def get_genre(message):
    db.insert_user_to_db(message.chat.id)
    curr_sessions = int([_ for _ in db.get_data_from_db(message.chat.id, "used_sessions")][0][0])
    if curr_sessions < USER_SESSION_LIMIT:
        db.update_db(message.chat.id,
                     columns=("used_sessions", "genre", "character", "setting", "add_info","used_tokens", "gpt_answer"),
                     values=(curr_sessions + 1, None, None, None, None, 0, "-",))
        bot.send_message(message.chat.id, "Для начала выбери жанр своей истории.\n"
                                          "Если хочешь выбрать свой жанр, просто напиши его в чат.",
                         reply_markup=add_buttons(("Хоррор", "Комедия", "Драма")))
        bot.register_next_step_handler(message, get_character)
    else:
        bot.send_message(message.chat.id, "Вы исчерпали лимит сессий")


def get_character(message):
    db.update_db(chat_id=message.chat.id, columns=("genre",), values=(message.text,))
    bot.send_message(message.chat.id, "Выбери главного героя своей истории.\n"
                                      "Если хочешь выбрать своего героя, просто напиши его в чат.",
                     reply_markup=add_buttons(("Доктор Хаус", "Доктор Дре", "Доктор Живаго", "Доктор Менгеле")))
    bot.register_next_step_handler(message, get_setting)


def get_setting(message):
    db.update_db(chat_id=message.chat.id, columns=("character",), values=(message.text,))
    bot.send_message(message.chat.id, "Выбери сеттинг своей истории.\n"
                                      "Если хочешь выбрать другой сеттинг, просто напиши его в чат.",
                     reply_markup=add_buttons(("Фантастика", "Космос", "Средневековье", "Пост апокалипсис")))
    bot.register_next_step_handler(message, get_add_info)


def get_add_info(message):
    db.update_db(chat_id=message.chat.id, columns=("setting",), values=(message.text,))
    bot.send_message(message.chat.id, "Если ты хочешь, чтобы мы учли ещё какую-то информацию, напиши её сейчас. Или "
                                      "ты можешь сразу переходить к истории написав /begin.",
                     reply_markup=add_buttons(("/begin", )))
    bot.register_next_step_handler(message, add_info_processing)


def add_info_processing(message):
    if message.text == "/begin":
        db.update_db(chat_id=message.chat.id, columns=("add_info",), values=("-",))
        send_gpt_answer(message)
    else:
        db.update_db(chat_id=message.chat.id, columns=("add_info",), values=(message.text,))
        send_gpt_answer(message)


def send_gpt_answer(message):
    curr_tokens = int([_ for _ in db.get_data_from_db(message.chat.id, "used_tokens")][0][0])
    if curr_tokens < USER_TOKEN_LIMIT:
        if message.text == "/end":
            answer, used_tokens = gpt.get_answer(message.chat.id, mode="end")
        elif [_ for _ in db.get_data_from_db(message.chat.id, "gpt_answer")][0][0]:
            answer, used_tokens = gpt.get_answer(message.chat.id, mode="continue")
        else:
            answer, used_tokens = gpt.get_answer(message.chat.id, mode="start")
        bot.send_message(message.chat.id, answer, reply_markup=add_buttons(("/end",)))
        db.update_db(message.chat.id, columns=("used_tokens",), values=(curr_tokens + used_tokens,))
        db.update_db(message.chat.id, columns=("gpt_answer",), values=(answer,), replace=False)
        if message.text == "/end":
            bot.send_message(message.chat.id, "Спасибо, что писал со мной историю. Можешь посмотреть нашу историю с помощью команды /wrote_history")
            return
        bot.register_next_step_handler(message, send_gpt_answer)
    else:
        bot.send_message(message.chat.id, "Вы исчерпали свой лимит токенов за сессию. Начните новую сессию командой /new_story",
                         reply_markup=add_buttons(("/new_story",)))


@bot.message_handler(commands=["wrote_history"])
def wrote_history(message):
    bot.send_message(message.chat.id, "Последняя написанная история: " + [_ for _ in db.get_data_from_db(message.chat.id, "gpt_answer")][0][0],
                     reply_markup=add_buttons(("/new_story",)))


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id,
                     f"Привет, {message.from_user.first_name} Я бот, который создаёт истории с помощью нейросети."
                     "Мы будем писать историю поочерёдно. Я начну, а ты продолжишь. Напиши /new_story, чтобы начать "
                     "новую историю. А когда ты закончишь, напиши /end.",
                     reply_markup=add_buttons(("/new_story",)))


@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id,
                     f"Привет, {message.from_user.first_name} Я бот, который создаёт истории с помощью нейросети."
                     "Мы будем писать историю поочерёдно. Я начну, а ты продолжишь. Напиши /new_story, чтобы начать "
                     "новую историю. А когда ты закончишь, напиши /end.",
                     reply_markup=add_buttons(("/new_story",)))


@bot.message_handler(commands=["debug"])
def debug(message):
    with open("logs.txt", "rb") as logs:
        bot.send_document(message.chat.id, logs)


@bot.message_handler(func=lambda message: True)
def text_message(message):
    bot.send_message(message.chat.id,
                     f"Привет, {message.from_user.first_name} Я бот, который создаёт истории с помощью нейросети."
                     "Мы будем писать историю поочерёдно. Я начну, а ты продолжишь. Напиши /new_story, чтобы начать "
                     "новую историю. А когда ты закончишь, напиши /end.",
                     reply_markup=add_buttons(("/new_story",)))


if __name__ == "__main__":
    db.create_table()
    bot.infinity_polling()
    logging.info("Бот запущен")
