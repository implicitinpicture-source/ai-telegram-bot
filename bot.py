!pip install gspread google-auth requests gigachat --quiet

import json
import requests
import gspread
import time
from google.colab import auth
from google.auth import default
from datetime import datetime
from gigachat import GigaChat

SHEET_ID = ''
BOT_TOKEN = ''
CHAT_ID = 
AUTH_KEY = ''

auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

if not worksheet.get_all_values():
    worksheet.append_row(["Дата","Имя","Тип запроса","Номер заказа","Описание","Срочность","Статус","Ошибка"])

giga = GigaChat(credentials=AUTH_KEY, verify_ssl_certs=False, model="GigaChat-3-Ultra")

def send_telegram(message):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        print("Ошибка Telegram:", e)

def process_message(text, client_chat_id):
    print(f"\n📩 Обработка от {client_chat_id}: {text[:60]}...")
    try:
        prompt = f"""Ты — система извлечения данных. Извлеки поля:
        - client_name (имя)
        - request_type (status|price|availability|other)
        - order_number (номер заказа)
        - description (краткое описание, до 100 символов)
        - urgency (true/false)

        Ответь ТОЛЬКО JSON.
        Формат: {{"client_name":"","request_type":"","order_number":"","description":"","urgency":false}}
        Текст: {text}"""
        response = giga.chat(prompt)
        parsed = json.loads(response.choices[0].message.content)
    except Exception as e:
        error_msg = f"GigaChat error: {str(e)}"
        print(error_msg)
        row = [datetime.now().strftime("%Y-%m-%d %H:%M"), "Ошибка", "ошибка", "ошибка", text[:100], "Нет", "ERROR", error_msg]
        worksheet.insert_row(row, 2)
        send_telegram(f"⚠️ Ошибка: {error_msg}")
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          json={"chat_id": client_chat_id, "text": "❌ Произошла ошибка. Попробуйте позже."})
        except:
            pass
        return

    client_name = parsed.get("client_name") or ""
    request_type = parsed.get("request_type") or "other"
    order_number = parsed.get("order_number") or ""
    description = parsed.get("description") or text[:100]
    urgency = "Да" if parsed.get("urgency") else "Нет"

    row = [datetime.now().strftime("%Y-%m-%d %H:%M"), client_name, request_type, order_number, description, urgency, "OK", ""]
    worksheet.insert_row(row, 2)

    print("✅ Таблица обновлена")
    send_telegram(f"📢 Новая заявка\n👤 Имя: {client_name or 'не указано'}\n📂 Тип: {request_type}\n📦 Заказ: {order_number or 'нет'}\n⚡️ Срочно: {urgency}")
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": client_chat_id, "text": f"✅ Спасибо, {client_name or 'друг'}! Ваша заявка принята."})
    except Exception as e:
        print("Ошибка отправки клиенту:", e)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset} if offset else {"timeout": 30}
    response = requests.get(url, params=params)
    return response.json().get("result", [])

print("🚀 Бот запущен. Жду сообщения...")
last_update_id = None
while True:
    updates = get_updates(last_update_id)
    for update in updates:
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            process_message(text, chat_id)
            last_update_id = update["update_id"] + 1
    time.sleep(2)
