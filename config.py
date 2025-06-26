# Импорт необходимых библиотек
import os
from dotenv import load_dotenv

# --- КОНФИГУРАЦИЯ ---
# Берем переменные окружения из файла .env
load_dotenv()

# Получаю токены из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Токен моего Telegram бота
API_KEY = os.getenv('KINOPOISK_API_KEY')  # API ключ для доступа к Kinopoisk
