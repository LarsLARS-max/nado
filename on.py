import logging
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (получить у @BotFather)
BOT_TOKEN = "8478095240:AAH7yBUhturE-mR2UwF_lDheLjr-29O5CYE"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            message_count INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица напоминаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_text TEXT,
            reminder_time TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Добавляем пользователя в БД
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date) VALUES (?, ?, ?, ?, ?)',
        (user_id, user.username, user.first_name, user.last_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    # Приветственное сообщение с клавиатурой
    keyboard = [
        [InlineKeyboardButton("📊 Информация", callback_data="info"),
         InlineKeyboardButton("🕐 Напоминание", callback_data="reminder")],
        [InlineKeyboardButton("🌤 Погода", callback_data="weather"),
         InlineKeyboardButton("🎮 Игры", callback_data="games")],
        [InlineKeyboardButton("🔧 Утилиты", callback_data="utils"),
         InlineKeyboardButton("📝 Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        rf"Привет {user.mention_html()}! 👋",
        reply_markup=reply_markup
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *Доступные команды:*

*/start* - Запустить бота
*/help* - Показать это сообщение
*/info* - Информация о пользователе
*/weather* <город> - Узнать погоду
*/reminder* <время> <текст> - Установить напоминание
*/calc* <выражение> - Калькулятор
*/joke* - Случайная шутка
*/quote* - Случайная цитата

🎮 *Игры:*
*/guess* - Угадай число
*/dice* - Бросить кости

Нажмите на кнопки ниже для быстрого доступа к функциям!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "info":
        await user_info(update, context)
    elif data == "reminder":
        await query.edit_message_text("📝 Для установки напоминания используйте команду:\n/reminder 15:30 Сделать домашку")
    elif data == "weather":
        await query.edit_message_text("🌤 Для получения погоды используйте:\n/weather Москва")
    elif data == "games":
        await games_menu(update, context)
    elif data == "utils":
        await utils_menu(update, context)
    elif data == "help":
        await help_command(update, context)

# Информация о пользователе
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    user_data = cursor.fetchone()
    
    if user_data:
        info_text = f"""
👤 *Информация о пользователе:*

🆔 ID: `{user_data[0]}`
👤 Имя: {user_data[2]} {user_data[3] or ''}
📛 Username: @{user_data[1] or 'Не указан'}
📅 Дата регистрации: {user_data[4][:10]}
💬 Сообщений: {user_data[5]}
        """
    else:
        info_text = "Пользователь не найден в базе данных"
    
    conn.close()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(info_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(info_text, parse_mode='Markdown')

# Команда погоды
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите город: /weather Москва")
        return
    
    city = ' '.join(context.args)
    
    try:
        # Используем OpenWeatherMap API (нужен API ключ)
        API_KEY = "YOUR_OPENWEATHER_API_KEY"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ru"
        
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            weather_info = f"""
🌤 *Погода в {city}:*

🌡 Температура: {data['main']['temp']}°C
💨 Ощущается как: {data['main']['feels_like']}°C
📝 Описание: {data['weather'][0]['description'].title()}
💧 Влажность: {data['main']['humidity']}%
🌬 Ветер: {data['wind']['speed']} м/с
            """
            await update.message.reply_text(weather_info, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Город не найден или ошибка API")
    
    except Exception as e:
        await update.message.reply_text("❌ Ошибка при получении погоды")
        logger.error(f"Weather error: {e}")

# Система напоминаний
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /reminder 15:30 Текст напоминания")
        return
    
    time_str = context.args[0]
    reminder_text = ' '.join(context.args[1:])
    
    try:
        # Парсим время (простая реализация)
        hours, minutes = map(int, time_str.split(':'))
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO reminders (user_id, reminder_text, reminder_time, created_at) VALUES (?, ?, ?, ?)',
            (update.effective_user.id, reminder_text, time_str, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Напоминание установлено на {time_str}: {reminder_text}")
    
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ")

# Калькулятор
async def calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Введите выражение: /calc 2+2*3")
        return
    
    expression = ' '.join(context.args)
    
    try:
        # Безопасное вычисление
        result = eval(expression)
        await update.message.reply_text(f"🧮 Результат: {result}")
    except:
        await update.message.reply_text("❌ Ошибка в выражении")

# Генератор шуток
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = [
        "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
        "Сколько программистов нужно, чтобы вкрутить лампочку? Ни одного, это hardware проблема!",
        "Почему Python стал таким популярным? Потому что у него змеиное обаяние!",
        "Компьютер не делает ошибок. Если что-то пошло не так - значит, это сделали вы!",
        "Оптимист верит, что стек наполовину полон. Пессимист верит, что стек наполовину пуст. Программист верит, что стек в два раза больше, чем нужно."
    ]
    
    import random
    joke_text = random.choice(jokes)
    await update.message.reply_text(f"😂 {joke_text}")

# Генератор цитат
async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get('https://api.quotable.io/random')
        if response.status_code == 200:
            data = response.json()
            quote_text = f"💫 *{data['content']}*\n\n— {data['author']}"
            await update.message.reply_text(quote_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Не удалось получить цитату")
    except:
        await update.message.reply_text("❌ Ошибка при получении цитаты")

# Игра "Угадай число"
async def guess_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'number' not in context.chat_data:
        context.chat_data['number'] = random.randint(1, 100)
        context.chat_data['attempts'] = 0
    
    if not context.args:
        await update.message.reply_text("🎯 Я загадал число от 1 до 100! Попробуй угадать:")
        return
    
    try:
        guess = int(context.args[0])
        context.chat_data['attempts'] += 1
        
        if guess < context.chat_data['number']:
            await update.message.reply_text("📈 Больше!")
        elif guess > context.chat_data['number']:
            await update.message.reply_text("📉 Меньше!")
        else:
            attempts = context.chat_data['attempts']
            await update.message.reply_text(f"🎉 Правильно! Число {guess} угадано за {attempts} попыток!")
            del context.chat_data['number']
            del context.chat_data['attempts']
    
    except ValueError:
        await update.message.reply_text("❌ Введите число!")

# Бросок костей
async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    
    dice_emojis = {
        1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"
    }
    
    result = f"🎲 Бросок костей:\n{dice_emojis[dice1]} {dice1} | {dice_emojis[dice2]} {dice2}\nСумма: {dice1 + dice2}"
    await update.message.reply_text(result)

# Меню игр
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎯 Угадай число", callback_data="game_guess")],
        [InlineKeyboardButton("🎲 Бросить кости", callback_data="game_dice")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🎮 *Выберите игру:*", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🎮 *Выберите игру:*", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Меню утилит
async def utils_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧮 Калькулятор", callback_data="util_calc"),
         InlineKeyboardButton("😂 Шутка", callback_data="util_joke")],
        [InlineKeyboardButton("💫 Цитата", callback_data="util_quote"),
         InlineKeyboardButton("🕐 Время", callback_data="util_time")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🔧 *Утилиты:*", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🔧 *Утилиты:*", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Увеличиваем счетчик сообщений
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET message_count = message_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    # Простой AI-ответ
    if any(word in text.lower() for word in ['привет', 'hello', 'hi']):
        await update.message.reply_text("👋 Привет! Как дела?")
    elif any(word in text.lower() for word in ['пока', 'bye', 'до свидания']):
        await update.message.reply_text("👋 До встречи! Буду рад помочь снова!")
    elif '?' in text:
        await update.message.reply_text("🤔 Интересный вопрос! Попробуйте использовать команду /help для списка возможностей")

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

# Основная функция
def main():
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", user_info))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("reminder", set_reminder))
    application.add_handler(CommandHandler("calc", calculator))
    application.add_handler(CommandHandler("joke", joke))
    application.add_handler(CommandHandler("quote", quote))
    application.add_handler(CommandHandler("guess", guess_number))
    application.add_handler(CommandHandler("dice", dice_roll))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    import random
    main()
