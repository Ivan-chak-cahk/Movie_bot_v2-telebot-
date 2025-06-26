import requests

# --- РАБОТА С API KINOPOISK ---
class KinopoiskAPI:
    # Базовый URL для API Kinopoisk (версия 1.4)
    BASE_URL = "https://api.kinopoisk.dev/v1.4/"

    def __init__(self, api_key):
        """
        Конструктор класса KinopoiskAPI
        api_key: Ключ для доступа к API Kinopoisk
        """
        self.api_key = api_key
        self.headers = {"X-API-KEY": self.api_key}  # Заголовки для HTTP-запросов, содержащие API ключ

    # Поиск фильмов по названию
    def search_by_name(self, name, limit=10, genre=None):
        # Параметры запроса
        params = {
            "query": name,  # Поисковый запрос
            "limit": limit  # Лимит результатов
        }
        # Добавление жанра в параметры, если он указан
        if genre:
            params["genres.name"] = genre
        # Отправка GET-запроса к API
        response = requests.get(
            f"{self.BASE_URL}movie/search",  # Конечная точка для поиска
            headers=self.headers,  # Заголовки с API ключом
            params=params  # Параметры запроса
        )
        return self.process_response(response)  # Обработка ответа

    # Поиск фильмов по рейтингу
    def search_by_rating(self, min_rating, max_rating, limit=10, genre=None):
        params = {
            "rating.kp": f"{min_rating}-{max_rating}",  # Диапазон рейтинга
            "limit": limit,
            "sortField": "rating.kp",  # Сортировка по рейтингу
            "sortType": "-1"  # Сортировка по убыванию (от высокого к низкому)
        }
        if genre:
            params["genres.name"] = genre

        response = requests.get(
            f"{self.BASE_URL}movie",
            headers=self.headers,
            params=params
        )
        return self.process_response(response)

    # Поиск фильмов по бюджету
    def search_by_budget(self, budget_type, limit=10, genre=None):
        # Определяем поле для сортировки в зависимости от типа бюджета
        sort_field = "budget" if budget_type == "high" else "-budget"
        params = {
            "limit": limit,
            "sortField": sort_field,  # Сортировка по бюджету
            "sortType": "1"  # По возрастанию
        }
        if genre:
            params["genres.name"] = genre

        response = requests.get(
            f"{self.BASE_URL}movie",
            headers=self.headers,
            params=params
        )
        return self.process_response(response)

    # Метод для обработки HTTP-ответов от API.
    def process_response(self, response):
        if response.status_code == 200:  # Если запрос успешен
            data = response.json()  # Парсим JSON ответ
            return data.get('docs', [])  # Возвращаем список фильмов или пустой список
        else:
            print(f"Error: {response.status_code}, {response.text}")  # Если ошибка
            return []  # Возвращаем пустой список

    # Получение детальной информации о конкретном фильме
    def get_movie_details(self, movie_id):
        response = requests.get(
            f"{self.BASE_URL}movie/{movie_id}",
            headers=self.headers
        )
        if response.status_code == 200:
            return response.json()  # Возвращаем полную информацию о фильме
        return None  # Возвращаем None при ошибке
