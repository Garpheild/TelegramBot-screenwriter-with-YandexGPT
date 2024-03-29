import requests
from config import GPT_MAX_TOKENS, URL, iam_token, FOLDER_ID, GPT_MODEL
import logging
import database as db

headers = {
    'Authorization': f'Bearer {iam_token}',
    'Content-Type': 'application/json'
}


def make_prompt(chat_id, mode, user_text=""):
    genre, character, setting, add_info, gpt_answer = (
        [_ for _ in db.get_data_from_db(chat_id=chat_id, columns="genre, character, setting, add_info, gpt_answer")][0])
    if mode == "start":
        return f"""Напиши историю с учетом следующих параметров:
                Жанр: {genre},Главный персонаж: {character},Сеттинг: {setting}, Дополнительная информация: {add_info}"""
    elif mode == "continue":
        return f"""Продолжи историю с учетом следующих параметров:
                Жанр: {genre},Главный персонаж: {character},Сеттинг: {setting}, Дополнительная информация: {add_info},
                Начало истории: {gpt_answer + user_text}"""
    elif mode == "end":
        return f"""Закончи историю с учетом следующих параметров:
                Жанр: {genre},Главный персонаж: {character},Сеттинг: {setting}, Дополнительная информация: {add_info},
                Начало истории: {gpt_answer}"""


def get_answer(chat_id, mode):

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": GPT_MAX_TOKENS
        },
        "messages": [
            {
                "role": "user",
                "text": make_prompt(chat_id, mode)
            }
        ]
    }

    response = requests.post(url=URL, headers=headers, json=data).json()
    if response:
        return response["result"]["alternatives"][0]["message"]["text"], int(response["result"]["usage"]["completionTokens"])
    else:
        logging.error(response)
        return "Ошибка при генерации запроса"
