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