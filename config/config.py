import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

 