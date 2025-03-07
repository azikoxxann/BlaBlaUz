import os
import telebot
import sqlite3
import re
import threading
import time
from flask import Flask

# Настройки
API_TOKEN = os.getenv("API_TOKEN")  # Берём токен из переменной окружения
bot = telebot.TeleBot(API_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает! 🚛"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    from threading import Thread
    
while True:
    try:
        bot.send_message(1087235453, "Проверка связи 🤖")
        time.sleep(45)  # Каждые 45 Секунд
    except Exception as e:
        print(f"Ошибка: {e}")

# Список городов Узбекистана
CITIES = [
    "Андижан", "Ташкент", "Фергана", "Бухара", "Джизак", "Карши", "Навои", "Наманган", "Самарканд", "Термез",
    "Гулистан", "Ургенч", "Нукус"
]

# Список марок автомобилей
CARS = [
    "Джентра", "Кобальт", "Каптива", "Малибу", "Авео", "Нексия", "Спарк", "Киа",
    "Орландо", "Трекер", "Эпика", "Каптива", "Оникс", "Эквинокс", "Хундай", "Траверс"
]

# База данных
conn = sqlite3.connect("rides.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS rides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    phone TEXT,
                    from_city TEXT,
                    to_city TEXT,
                    car_model TEXT,
                    price INTEGER,
                    seats INTEGER,
                    created_at INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    phone TEXT)''')
conn.commit()

# Команды
@bot.message_handler(commands=['start'])
def start_cmd(message):
    # Проверка наличия номера телефона в базе данных
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
    keyboard.add("🚗 Создать поездку", "✏️ Изменить поездку", "❌ Удалить поездку")
    bot.send_message(message.chat.id, "Отлично! Вы можете создать, изменить или удалить поездку.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🚌 Пассажир")
def passenger_choice(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔍 Найти поездку", "📋 Просмотреть все поездки")
    bot.send_message(message.chat.id, "Отлично! Вы можете найти поездку или просмотреть все доступные поездки.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "🚗 Создать поездку")
def create_ride(message):
    cursor.execute("SELECT COUNT(*) FROM rides WHERE driver_id=?", (message.from_user.id,))
    ride_count = cursor.fetchone()[0]
    if ride_count >= 2:
        bot.send_message(message.chat.id, "Вы не можете создать более двух поездок.")
        return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in CITIES:
        markup.add(city)
    bot.send_message(message.chat.id, "Выберите город отправления:", reply_markup=markup)
    bot.register_next_step_handler(message, get_to_city)

def get_to_city(message):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    from_city = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in CITIES:
        if city != from_city:
            markup.add(city)
    bot.send_message(message.chat.id, "Выберите город назначения:", reply_markup=markup)
    bot.register_next_step_handler(message, get_car_model, from_city)

def get_car_model(message, from_city):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    to_city = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for car in CARS:
        markup.add(car)
    markup.add("Другая марка")
    bot.send_message(message.chat.id, "Выберите марку автомобиля или введите вручную:", reply_markup=markup)
    bot.register_next_step_handler(message, process_car_model, from_city, to_city)

def process_car_model(message, from_city, to_city):
    car_model = message.text
    if car_model == "Другая марка":
        bot.send_message(message.chat.id, "Введите марку автомобиля:")
        bot.register_next_step_handler(message, get_price, from_city, to_city)
    else:
        get_price(message, from_city, to_city, car_model)

def get_price(message, from_city, to_city, car_model=None):
    if car_model is None:
        car_model = message.text
    bot.send_message(message.chat.id, "Введите цену за поездку:")
    bot.register_next_step_handler(message, get_seats, from_city, to_city, car_model)

def get_seats(message, from_city, to_city, car_model):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введите корректное число для цены!")
        return
    price = int(message.text)
    bot.send_message(message.chat.id, "Сколько мест в машине?")
    bot.register_next_step_handler(message, save_ride, from_city, to_city, car_model, price)

def save_ride(message, from_city, to_city, car_model, price):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введите корректное число для мест!")
        return
    seats = int(message.text)
    try:
        cursor.execute("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,))
        phone = cursor.fetchone()[0]
        created_at = int(time.time())
        cursor.execute("INSERT INTO rides (driver_id, phone, from_city, to_city, car_model, price, seats, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (message.from_user.id, phone, from_city, to_city, car_model, price, seats, created_at))
        conn.commit()
        bot.send_message(message.chat.id, "🚗 Ваша поездка успешно добавлена!")
        show_main_menu(message)  # Возвращаемся в начальное меню после успешного добавления поездки
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при сохранении поездки: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "❌ Удалить поездку")
def delete_ride(message):
    cursor.execute("SELECT * FROM rides WHERE driver_id=?", (message.from_user.id,))
    rides = cursor.fetchall()
    if not rides:
        bot.send_message(message.chat.id, "У вас нет доступных поездок для удаления.")
        return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ride in rides:
        markup.add(f"{ride[3]} ➡ {ride[4]} (ID: {ride[0]})")
    bot.send_message(message.chat.id, "Выберите поездку для удаления:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_delete_ride)

def confirm_delete_ride(message):
    try:
        ride_id = int(re.search(r"ID: (\d+)", message.text).group(1))
        cursor.execute("DELETE FROM rides WHERE id=? AND driver_id=?", (ride_id, message.from_user.id))
        conn.commit()
        bot.send_message(message.chat.id, "❌ Поездка успешно удалена!")
        show_main_menu(message)  # Возвращаемся в начальное меню после успешного удаления поездки
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при удалении поездки: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "✏️ Изменить поездку")
def edit_ride(message):
    cursor.execute("SELECT * FROM rides WHERE driver_id=?", (message.from_user.id,))
    rides = cursor.fetchall()
    if not rides:
        bot.send_message(message.chat.id, "У вас нет доступных поездок для изменения.")
        return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ride in rides:
        markup.add(f"{ride[3]} ➡ {ride[4]} (ID: {ride[0]})")
    bot.send_message(message.chat.id, "Выберите поездку для изменения:", reply_markup=markup)
    bot.register_next_step_handler(message, select_ride_to_edit)

def select_ride_to_edit(message):
    try:
        ride_id = int(re.search(r"ID: (\d+)", message.text).group(1))
        cursor.execute("SELECT * FROM rides WHERE id=? AND driver_id=?", (ride_id, message.from_user.id))
        ride = cursor.fetchone()
        if ride:
            edit_ride_details(message, ride)
        else:
            bot.send_message(message.chat.id, "Не удалось найти поездку. Попробуйте снова.")
            edit_ride(message)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при выборе поездки: {str(e)}")

def edit_ride_details(message, ride):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Изменить город отправления", "Изменить город назначения", "Изменить марку автомобиля", "Изменить цену", "Изменить количество мест")
    bot.send_message(message.chat.id, "Что вы хотите изменить?", reply_markup=keyboard)
    bot.register_next_step_handler(message, handle_edit_choice, ride)

def handle_edit_choice(message, ride):
    if message.text == "Изменить город отправления":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for city in CITIES:
            markup.add(city)
        bot.send_message(message.chat.id, "Выберите новый город отправления:", reply_markup=markup)
        bot.register_next_step_handler(message, update_from_city, ride)
    elif message.text == "Изменить город назначения":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for city in CITIES:
            markup.add(city)
        bot.send_message(message.chat.id, "Выберите новый город назначения:", reply_markup=markup)
        bot.register_next_step_handler(message, update_to_city, ride)
    elif message.text == "Изменить марку автомобиля":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for car in CARS:
            markup.add(car)
        markup.add("Другая марка")
        bot.send_message(message.chat.id, "Выберите новую марку автомобиля или введите вручную:", reply_markup=markup)
        bot.register_next_step_handler(message, update_car_model, ride)
    elif message.text == "Изменить цену":
        bot.send_message(message.chat.id, "Введите новую цену за поездку:")
        bot.register_next_step_handler(message, update_price, ride)
    elif message.text == "Изменить количество мест":
        bot.send_message(message.chat.id, "Введите новое количество мест:")
        bot.register_next_step_handler(message, update_seats, ride)
    else:
        bot.send_message(message.chat.id, "Неверный выбор. Попробуйте снова.")
        edit_ride_details(message, ride)

def update_from_city(message, ride):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    new_from_city = message.text
    cursor.execute("UPDATE rides SET from_city=? WHERE id=?", (new_from_city, ride[0]))
    conn.commit()
    bot.send_message(message.chat.id, "Город отправления успешно обновлен!")
    show_main_menu(message)

def update_to_city(message, ride):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    new_to_city = message.text
    cursor.execute("UPDATE rides SET to_city=? WHERE id=?", (new_to_city, ride[0]))
    conn.commit()
    bot.send_message(message.chat.id, "Город назначения успешно обновлен!")
    show_main_menu(message)

def update_car_model(message, ride):
    car_model = message.text
    if car_model == "Другая марка":
        bot.send_message(message.chat.id, "Введите марку автомобиля:")
        bot.register_next_step_handler(message, save_car_model, ride)
    else:
        cursor.execute("UPDATE rides SET car_model=? WHERE id=?", (car_model, ride[0]))
        conn.commit()
        bot.send_message(message.chat.id, "Марка автомобиля успешно обновлена!")
        show_main_menu(message)

def save_car_model(message, ride):
    car_model = message.text
    cursor.execute("UPDATE rides SET car_model=? WHERE id=?", (car_model, ride[0]))
    conn.commit()
    bot.send_message(message.chat.id, "Марка автомобиля успешно обновлена!")
    show_main_menu(message)

def update_price(message, ride):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введите корректное число для цены!")
        return
    new_price = int(message.text)
    cursor.execute("UPDATE rides SET price=? WHERE id=?", (new_price, ride[0]))
    conn.commit()
    bot.send_message(message.chat.id, "Цена успешно обновлена!")
    show_main_menu(message)

def update_seats(message, ride):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введите корректное число для мест!")
        return
    new_seats = int(message.text)
    cursor.execute("UPDATE rides SET seats=? WHERE id=?", (new_seats, ride[0]))
    conn.commit()
    bot.send_message(message.chat.id, "Количество мест успешно обновлено!")
    show_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "🔍 Найти поездку")
def search_ride(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in CITIES:
        markup.add(city)
    bot.send_message(message.chat.id, "Выберите город отправления:", reply_markup=markup)
    bot.register_next_step_handler(message, search_to_city)

def search_to_city(message):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    from_city = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for city in CITIES:
        if city != from_city:
            markup.add(city)
    bot.send_message(message.chat.id, "Выберите город назначения:", reply_markup=markup)
    bot.register_next_step_handler(message, show_rides, from_city)

def show_rides(message, from_city):
    if message.text not in CITIES:
        bot.send_message(message.chat.id, "Пожалуйста, выберите город из списка!")
        return
    to_city = message.text
    cursor.execute("SELECT * FROM rides WHERE from_city=? AND to_city=?", (from_city, to_city))
    rides = cursor.fetchall()
    if rides:
        response = "🚗 Доступные поездки:\n"
        for r in rides:
            response += f"📍 {r[3]} ➡ {r[4]}\n🚗 Марка автомобиля: {r[5]}\n💰 Цена: {r[6]} руб.\n🪑 Мест: {r[7]}\n📞 Телефон: {r[2]}\n\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "❌ Поездок не найдено.")
    show_main_menu(message)  # Возвращаемся в начальное меню после поиска поездок

@bot.message_handler(func=lambda message: message.text == "📋 Просмотреть все поездки")
def view_all_rides(message):
    cursor.execute("SELECT * FROM rides")
    rides = cursor.fetchall()
    if rides:
        response = "🚗 Все доступные поездки:\n"
        for r in rides:
            response += f"📍 {r[3]} ➡ {r[4]}\n🚗 Марка автомобиля: {r[5]}\n💰 Цена: {r[6]} руб.\n🪑 Мест: {r[7]}\n📞 Телефон: {r[2]}\n\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "❌ Доступных поездок не найдено.")
    show_main_menu(message)  # Возвращаемся в начальное меню после просмотра всех поездок

# Функция для удаления старых поездок
def delete_old_rides():
    while True:
        current_time = int(time.time())
        cursor.execute("DELETE FROM rides WHERE ? - created_at >= 86400", (current_time,))
        conn.commit()
        time.sleep(3600)  # Проверяем каждый час

# Запуск потока для удаления старых поездок
threading.Thread(target=delete_old_rides, daemon=True).start()

# Запуск бота
if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в работе бота: {str(e)}")
        
  # Запускаем бота в отдельном потоке
    Thread(target=run_bot).start()

    # Запускаем Gunicorn/Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
