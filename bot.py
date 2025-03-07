import os
import telebot
import sqlite3
import re
import time
import threading
from flask import Flask

# === 1. Инициализация Flask (чтобы Render не требовал порт) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# === 2. Настройки бота ===
API_TOKEN = os.getenv("API_TOKEN")  # Токен бота
bot = telebot.TeleBot(API_TOKEN)

# === 3. Подключение к SQLite (без блокировки) ===
def get_db_connection():
    return sqlite3.connect("rides.db", check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS rides (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            driver_id INTEGER,
                            phone TEXT,
                            from_city TEXT,
                            to_city TEXT,
                            created_at INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            phone TEXT)''')
        conn.commit()

# === 4. Запуск инициализации базы ===
init_db()

# === 5. Команда /start ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,))
        user = cursor.fetchone()

    if user:
        show_main_menu(message)
    else:
        bot.send_message(message.chat.id, "Введите ваш номер телефона (в формате +998xxxxxxxxx):")
        bot.register_next_step_handler(message, save_user_phone)

def save_user_phone(message):
    phone = message.text.strip()
    if not re.match(r"^\+998\d{9}$", phone):
        bot.send_message(message.chat.id, "❌ Неверный формат! Введите номер в формате +998xxxxxxxxx:")
        bot.register_next_step_handler(message, save_user_phone)
        return

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, phone) VALUES (?, ?)", (message.from_user.id, phone))
        conn.commit()

    bot.send_message(message.chat.id, "✅ Ваш номер телефона успешно сохранен!")
    show_main_menu(message)

def show_main_menu(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🚗 Водитель", "🚌 Пассажир")
    bot.send_message(message.chat.id, "Привет! Выберите, пожалуйста, кто вы:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🚗 Водитель")
def driver_choice(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🚗 Создать поездку", "❌ Удалить поездку")
    bot.send_message(message.chat.id, "Вы можете создать или удалить поездку.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🚗 Создать поездку")
def create_ride(message):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rides WHERE driver_id=?", (message.from_user.id,))
        ride_count = cursor.fetchone()[0]

    if ride_count >= 2:
        bot.send_message(message.chat.id, "Вы не можете создать более двух поездок.")
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in ["Ташкент", "Самарканд", "Бухара"]:  # Ограничил список для примера
        markup.add(city)
    bot.send_message(message.chat.id, "Выберите город отправления:", reply_markup=markup)
    bot.register_next_step_handler(message, get_to_city)

def get_to_city(message):
    from_city = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in ["Ташкент", "Самарканд", "Бухара"]:
        if city != from_city:
            markup.add(city)
    bot.send_message(message.chat.id, "Выберите город назначения:", reply_markup=markup)
    bot.register_next_step_handler(message, save_ride, from_city)

def save_ride(message, from_city):
    to_city = message.text
    created_at = int(time.time())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rides (driver_id, phone, from_city, to_city, created_at) VALUES (?, ?, ?, ?, ?)",
                       (message.from_user.id, "Номер скрыт", from_city, to_city, created_at))
        conn.commit()

    bot.send_message(message.chat.id, "🚗 Ваша поездка успешно добавлена!")
    show_main_menu(message)

# === 6. Удаление старых поездок (в фоновом потоке) ===
def delete_old_rides():
    while True:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rides WHERE strftime('%s', 'now') - created_at >= 86400")
            conn.commit()
        time.sleep(3600)  # Проверяем каждый час

# === 7. Запуск фонового процесса ===
threading.Thread(target=delete_old_rides, daemon=True).start()

# === 8. Запуск бота и Flask в отдельных потоках ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {str(e)}")
