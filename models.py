# Импорт необходимых библиотек
from peewee import *
import datetime

# --- БАЗА ДАННЫХ ---
# Создаем соединение с SQLite базой данных
db = SqliteDatabase('movies.db')

# Базовый класс модели для наследования
class BaseModel(Model):
    class Meta:
        database = db  # Все модели будут использовать эту БД

# Модель пользователя Telegram
class User(BaseModel):
    telegram_id = IntegerField(unique=True)  # Уникальный ID пользователя в Telegram
    username = CharField(null=True)  # Имя пользователя в телеграм
    created_at = DateTimeField(default=datetime.datetime.now)  # Дата регистрации

# Модель истории поисковых запросов
class SearchHistory(BaseModel):
    user = ForeignKeyField(User, backref='searches')  # Связь с пользователем
    search_type = CharField()  # Тип поиска
    query = TextField(null=True)  # Текст запроса
    min_rating = FloatField(null=True)  # Мин рейтинг
    max_rating = FloatField(null=True)  # Макс рейтинг
    budget_type = CharField(null=True)  # Бюджет
    genre = CharField(null=True)  # Жанр
    results_count = IntegerField()  # Счетчик результатов
    created_at = DateTimeField(default=datetime.datetime.now) # Время поиска

# Модель фильмов и сериалов
class Movie(BaseModel):
    kp_id = IntegerField(unique=True)  # ID фильма в Kinopoisk API
    name = CharField(null=True)  # Название фильма
    description = TextField(null=True)  # Описание
    rating_kp = FloatField(null=True)  # Рейтинг
    year = IntegerField(null=True)  # Год выпуска
    genres = CharField()  # Жанры (строка с перечислением)
    age_rating = CharField(null=True)  # Возрастной рейтинг
    poster_url = TextField(null=True)  # Ссылка на постер(если есть)

# Модель результатов поиска
class SearchResult(BaseModel):
    search = ForeignKeyField(SearchHistory, backref='results')  # Связь с поисковыми запросами
    movie = ForeignKeyField(Movie)  # Связь с фильмами и сериалами
    is_watched = BooleanField(default=False)  # отметка о просмотре

# функция для создания таблицы
def create_tables():
    with db:
        db.create_tables([User, SearchHistory, Movie, SearchResult])

if __name__ == '__main__':
    create_tables()
