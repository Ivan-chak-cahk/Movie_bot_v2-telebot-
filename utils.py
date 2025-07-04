from telebot import types
from telebot.types import InlineKeyboardButton

from models import Movie

def create_main_keyboard():
    # Создаем клавиатуру с автоматическим изменением размера под экран
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Добавление кнопок
    keyboard.add(
        types.KeyboardButton("Поиск по названию"),
        types.KeyboardButton("Поиск по рейтингу"),
        types.KeyboardButton("Поиск по бюджету"),
        types.KeyboardButton("История поиска"),
        types.KeyboardButton("Помощь"),
    )
    return keyboard

def create_genre_keyboard():
    # клава для выбора жанра
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)  # 3 кнопки в ряд
    genres = [
        "боевик", "комедия", "фантастика", "ужасы",
        "триллер", "драма", "мелодрама", "детектив",
        "фэнтези", "приключения", "аниме", "мультфильм"
    ]
    keyboard.add(
        *[types.KeyboardButton(gener) for gener in genres],
        types.KeyboardButton("Пропустить"),
    )
    return keyboard

def create_count_keyboard():
    # клава для выбора количества выводимых результатов поискового запроса
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
    keyboard.add(*[types.KeyboardButton(str(i)) for i in range(1,11)])
    return keyboard

def create_watch_keyboard(movie_id):
    # Инлайн клава для отметки просмотренных фильмов
    keyboard = types.InlineKeyboardMarkup()
    # Добавляем инлайн-кнопку с callback-данными, содержащими ID фильма
    keyboard.add(InlineKeyboardButton(
        text="Отметить как просмотренный",
        callback_data=f"watched_{movie_id}"
    ))
    return keyboard

def format_movie_info(movie_data):
    # Форматируем информацию для удобного вывода пользователю в тг
    # Определяем источник данных (API или БД)
    if isinstance(movie_data, Movie):
        # Если это объект Movie из базы данных
        movie_info = {
            'name': movie_data.name,
            'description': movie_data.description,
            'rating': movie_data.rating_kp,
            'year': movie_data.year,
            'genres': movie_data.genres,
            'age_rating': movie_data.age_rating,
            'poster': movie_data.poster_url
        }
    else:
        # Если это данные из API
        movie_info = {
            'name': movie_data.get('name'),
            'description': movie_data.get('description'),
            'rating': movie_data.get('rating', {}).get('kp'),
            'year': movie_data.get('year'),
            'genres': ', '.join(g.get('name', '') for g in movie_data.get('genres', [])),
            'age_rating': movie_data.get('ageRating'),
            'poster': movie_data.get('poster', {}).get('url')
        }

    # Формируем текст с значениями по умолчанию
    text = (
        f"<b>{movie_info['name'] or 'Название не указано'}</b> "
        f"({movie_info['year'] or 'Год не указан'})\n"
        f"Рейтинг KP: <b>{movie_info['rating'] or 'Нет рейтинга'}</b>\n"
        f"Жанр: <b>{movie_info['genres'] or 'Жанр не указан'}</b>\n"
        f"Возрастной рейтинг: <b>{movie_info['age_rating'] or 'Не указан'}</b>\n\n"
        f"<i>{(movie_info['description'] or 'Описание отсутствует')[:300]}</i>"
    )

    return text, movie_info['poster']
