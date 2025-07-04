import telebot
from telebot import types
from config import TOKEN, API_KEY
from models import Movie, SearchResult, SearchHistory, User, create_tables
from kinopoisk_api import KinopoiskAPI
from utils import (
    create_main_keyboard, create_count_keyboard,
    create_genre_keyboard, create_watch_keyboard,
    format_movie_info
)
import datetime

# Инициализация бота и API
bot = telebot.TeleBot(TOKEN)  # Создание экземпляра бота
kp_api = KinopoiskAPI(API_KEY)  # Создание экземпляра API Kinopoisk

# Создание таблиц БД при запуске
create_tables()

# Словарь для хранения состояний пользователей
user_states = {}


class UserState:
    """Класс для хранения состояния диалога с пользователем"""
    def __init__(self):
        self.search_type = None  # Тип текущего поиска
        self.search_query = None  # Введенный поисковый запрос
        self.min_rating = None  # Минимальный рейтинг для фильтрации
        self.max_rating = None  # Максимальный рейтинг
        self.budget_type = None  # 'high' или 'low' для поиска по бюджету
        self.genre = None  # Выбранный жанр для фильтрации
        self.results_count = 5  # Количество возвращаемых результатов (по умолчанию 5)
        self.current_page = 0  # Текущая страница пагинации
        self.search_results = []  # Список найденных фильмов


def get_or_create_user(telegram_id):
    """Получает пользователя из БД или создает нового"""
    user, created = User.get_or_create(telegram_id=telegram_id)
    return user


def save_search_history(user, state):
    """Сохраняет историю поиска и результаты в БД"""
    # Создание записи о поисковом запросе
    search = SearchHistory.create(
        user=user,
        search_type=state.search_type,
        query=state.search_query,
        min_rating=state.min_rating,
        max_rating=state.max_rating,
        budget_type=state.budget_type,
        genre=state.genre,
        results_count=state.results_count
    )
    # Сохранение каждого найденного фильма
    for movie_data in state.search_results:
        # Создание или обновление информации о фильме
        movie, created = Movie.get_or_create(
            kp_id=movie_data.get('id'),
            defaults={
                'name': movie_data.get('name'),
                'description': movie_data.get('description'),
                'rating_kp': movie_data.get('rating', {}).get('kp'),
                'year': movie_data.get('year'),
                'genres': ', '.join([g.get('name', '') for g in movie_data.get('genres', [])]),
                'age_rating': movie_data.get('ageRating'),
                'poster_url': movie_data.get('poster', {}).get('url') if movie_data.get('poster') else None
            }
        )
        # Связывание фильма с поисковым запросом
        SearchResult.create(
            search=search,
            movie=movie,
            is_watched=False  # По умолчанию помечается как непросмотренный
        )
    return search

# Обработчики команд
@bot.message_handler(commands=["start"])
def handel_start(message):
    """Приветствие и главное меню"""
    user = get_or_create_user(message.from_user.id)  # Регистрация пользователя
    bot.send_message(
        message.chat.id,
        "Добро пожаловать в MovieSearchBot!\n\n"
        "Я помогу вам найти информацию о фильмах и сериалах с Kinopoisk.\n"
        "Используйте кнопки ниже для навигации.",
        reply_markup=create_main_keyboard()  # Показ главного меню
    )


@bot.message_handler(commands=["help"])
def handel_help(message):
    """Справка по командам"""
    help_text = (
        "<b>Доступные команды:</b>\n\n"
        "<b>Поиск по названию</b> - найти фильм по названию\n"
        "<b>Поиск по рейтингу</b> - найти фильмы в указанном диапазоне рейтинга\n"
        "<b>Поиск по бюджету</b> - найти фильмы с высоким или низким бюджетом\n"
        "<b>История поиска</b> - просмотреть историю ваших запросов\n\n"
        "После поиска вы можете отмечать фильмы как просмотренные."
    )
    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode="HTML"
    )


@bot.message_handler(commands=["history"])
def handel_history(message):
    """Показ меню истории поиска"""
    user = get_or_create_user(message.from_user.id)
    show_history_menu(message.chat.id, user)

def show_history_menu(chat_id, user):
    """Отображение меню истории"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("Последние 5 запросов"),
        types.KeyboardButton("Назад в меню")
    )
    bot.send_message(
        chat_id,
        "Выберите вариант просмотра истории:",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text == "Помощь")
def handel_help_button(message):
    """
    Если написать в чате с ботом "Помощь", то вызовется
    команда help?
    """
    handel_help(message)

@bot.message_handler(func=lambda message: message.text =="История поиска")
def handel_history_button(message):
    user = get_or_create_user(message.from_user.id)
    show_history_menu(message.chat.id, user)

# История поиска
@bot.message_handler(func=lambda message: message.text == "Последние 5 запросов")
def handel_last_5_searches(message):
    user = get_or_create_user(message.from_user.id)
    # Запрос к БД с сортировкой по дате и ограничением 5
    searches = (SearchHistory
                .select()
                .where(SearchHistory.user == user)
                .order_by(SearchHistory.created_at.desc())
                .limit(5)
                )
    if not searches:
        bot.send_message(message.chat.id, "Ваша история поиска пуста")
        return

    # Формирование сообщения для каждого запроса
    for search in searches:
        results = (SearchResult
                  .select()
                  .where(SearchResult.search == search)
                  .join(Movie)
                  )

        text = {
            f"<b>{search.created_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"Тип поиска: <b>{search.search_type}</b>\n"
            f"Найдено результатов: <b>{results.count()}</b>\n\n"
            "Нажмите на кнопку ниже для просмотра результатов:"
        }

        # Создание inline-кнопки для просмотра результатов
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="Показать результат",
            callback_data=f"show_search_{search.id}"
        ))

        bot.send_message(
            message.chat.id,
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

# Обработчик inline-кнопки для показа результатов поиска
@bot.callback_query_handler(func=lambda call: call.data.startswith("show_search_"))
def show_search_result(call):
    # Извлекаем ID поиска из callback_data (формат 'show_search_123')
    search_id = int(call.data.split("_")[2])
    # Получаем запись о поиске из базы данных
    search = SearchHistory.get_by_id(search_id)
    # Получаем все результаты этого поиска с информацией о фильмах
    results = (SearchResult
               .select()
               .where(SearchResult.search == search)
               .join(Movie)  # Соединяем с таблицей фильмов
               .order_by(SearchResult.id)  # Сортируем по ID
               )
    # Для каждого результата формируем и отправляем сообщение
    for result in results:
        # Форматируем информацию о фильме
        text, poster_url = format_movie_info(result.movie)
        # Создаем inline-клавиатуру с кнопкой "Отметить просмотренным"
        keyboard = create_watch_keyboard(result.id)
        if poster_url:
            # Если есть постер, отправляем фото с описанием
            bot.send_photo(
                call.message.chat.id,
                poster_url,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            # Если постера нет, отправляем просто текст
            bot.send_photo(
                call.message.chat.id,
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
    # Подтверждаем обработку callback-запроса
    bot.answer_callback_query(call.id)

# Обработчик для отметки фильма просмотренным
@bot.callback_query_handler(func=lambda call: call.data.startswith("watched_"))
def mark_as_watched(call):
    result_id = int(call.data.split("_")[1])
    result = SearchResult.get_by_id(result_id)
    # Инвертируем текущий статус просмотра
    result.is_watched = not result.is_watched
    result.save() # Сохраняем изменения в БД
    # Формируем текст подтверждения
    status = "просмотрен" if result.is_watched else "не просмотрен"
    # Отправляем уведомление пользователю
    bot.answer_callback_query(
        call.id,
        f"Фильм отмечен как{status}",
        show_alert=False  # Всплывающее уведомление (не блокирующее)
    )

# возврат в основное меню
@bot.message_handler(func=lambda message: message.text == "Назад в меню")
def back_to_menu(message):
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=create_main_keyboard()
    )

# Обработчик для поиска по названию
@bot.message_handler(func=lambda message: message.text == "Поиск по названию")
def search_by_name(message):
    """Инициация поиска по названию"""
    user_states[message.from_user.id] = UserState()  # Создание состояния
    user_states[message.from_user.id].search_type = "Поиск по названию"

    msg = bot.send_message(
        message.chat.id,
        "Введите название фильма или сериала:",
        reply_markup=types.ReplyKeyboardRemove()  # Скрытие клавиатуры
    )
    # Ожидание ввода названия
    bot.register_next_step_handler(msg, process_name_input)


def process_name_input(message):
    """Обработка введенного названия"""
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = UserState()

    user_states[user_id].search_query = message.text  # Сохранение запроса

    # Запрос жанра для фильтрации(если нужно)
    msg = bot.send_message(
        message.chat.id,
        "Хотите указать жанр? (или нажмите 'Пропустить')",
        reply_markup=create_genre_keyboard()
    )
    bot.register_next_step_handler(msg, process_genre_input)

# Обработчик для поиска по рейтингу
@bot.message_handler(func=lambda message: message.text == "Поиск по рейтингу")
def search_by_rating(message):
    """Инициация поиска по рейтингу"""
    user_states[message.from_user.id] = UserState()  # Создание состояния
    user_states[message.from_user.id].search_type = "Поиск по рейтингу"

    msg = bot.send_message(
        message.chat.id,
        "Введите диапазон рейтинга (в формате '1-10')",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_rating_input)


def process_rating_input(message):
    """Обработка введенного диапазона рейтинга"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            user_states[user_id] = UserState()

        # Парсинг диапазона (например, "7-9")
        min_rating, max_rating = map(float, message.text.split("-"))
        user_states[user_id].min_rating = min_rating
        user_states[user_id].max_rating = max_rating

        # Запрос жанра для фильтрации
        msg = bot.send_message(
            message.chat.id,
            "Хотите указать жанр? (или нажмите 'Пропустить')",
            reply_markup=create_genre_keyboard()
        )
        bot.register_next_step_handler(msg, process_genre_input)

    except (ValueError, AttributeError):
        # Обработка ошибки неверного формата
        bot.send_message(
            message.chat.id,
            "Неверный формат. Введите диапазон в формате '1-10'",  # ???????
            search_by_rating(message)  # Повторный запрос
        )

# Обработчик для поиска по бюджету
@bot.message_handler(func=lambda message: message.text == "Поиск по бюджету")
def search_by_rating(message):
    """Инициация поиска по бюджету"""
    user_states[message.from_user.id] = UserState()  # Создание состояния
    user_states[message.from_user.id].search_type = "Поиск по бюджету"
    # клава для выбора бюджета
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("Высокий бюджет"),
        types.KeyboardButton("Низкий бюджет")
    )

    msg = bot.send_message(
        message.chat.id,
        "Выберете тип бюджета:",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, process_budget_type_input)


def process_budget_type_input(message):
    """Обработка выбора бюджета"""
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = UserState()

    if message.text == "Высокий бюджет":
        user_states[user_id].budget_type = "high"
    elif message.text == "Низкий бюджет":
        user_states[user_id].budget_type = "low"
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите один из предложенных вариантов"
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "Хотите указать жанр? (или нажмите 'Пропустить')",
        reply_markup=create_genre_keyboard()
    )
    bot.register_next_step_handler(msg, process_genre_input)


def process_genre_input(message):
    """Обработка выбора жанра"""
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = UserState()

    if message.text != "Пропустить":
        user_states[user_id].genre = message.text  # Сохранение жанра

    # Запрос количества результатов
    msg = bot.send_message(
        message.chat.id,
        "Сколько результатов показать от 1 до 10?:",
        reply_markup=create_count_keyboard()  # Клавиатура с цифрами
    )
    bot.register_next_step_handler(msg, process_count_input)


def process_count_input(message):
    """Обработка количества результатов"""
    try:
        user_id = message.from_user.id
        if user_id not in user_states:
            user_states[user_id] = UserState()

        count = int(message.text)
        if 1 <= count <= 10:
            user_states[user_id].results_count = count
            perform_search(message)  # Запуск поиска
        else:
            # Ошибка: число вне диапазона
            bot.send_message(
                message.chat.id,
                "Пожалуйста, введите число от 1 до 10"
            )
            # Повторный запрос
            msg = bot.send_message(
                message.chat.id,
                "Сколько результатов показать? (1-10)",
                reply_markup=create_count_keyboard()
            )
            bot.register_next_step_handler(msg, process_count_input)

    except ValueError:
        # Ошибка: введено не число
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите число от 1 до 10"
        )
        msg = bot.send_message(
            message.chat.id,
            "Сколько результатов показать? (1-10)",
            reply_markup=create_count_keyboard()
        )
        bot.register_next_step_handler(msg, process_count_input)