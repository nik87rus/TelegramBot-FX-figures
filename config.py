from os import environ
from dotenv import load_dotenv

# Загрузка значений переменных окружения
load_dotenv()

token = environ.get('token')




