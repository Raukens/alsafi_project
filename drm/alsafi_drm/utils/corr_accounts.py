import json
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.conf import settings

CACHE_KEY = "corr_accounts_data"
CACHE_TTL = 6 * 60 * 60

# Файл-заглушка для локальной разработки (относительно корня репозитория)
MOCK_JSON_PATH = "lcr_json.txt"


def _mock_corr_data():
    """Заглушка для локальной разработки: данные из lcr_json.txt."""
    path = settings.BASE_DIR.parent / MOCK_JSON_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "data": {
                "assets": [],
                "liabilities": [],
                "data": {},
                "bufferByBank": [],
            }
        }
    # В файле структура data.data.assets / data.data.liabilities; вьюхи ждут data["data"]["assets"]
    inner = (loaded.get("data") or {}).get("data")
    if isinstance(inner, dict):
        return {"data": inner}
    return loaded


def fetch_corr_accounts():
    session = requests.Session()
    session.verify = False

    # Шаг 1: получить форму логина
    r = session.get(settings.CORR_ACCOUNTS_URL, allow_redirects=True)
    soup = BeautifulSoup(r.text, 'html.parser')
    form = soup.find('form')
    if not form:
        raise Exception("Форма логина не найдена")
    login_url = form.get('action')

    # Шаг 2: залогиниться
    session.post(login_url, data={
        "username": settings.CORR_ACCOUNTS_LOGIN,
        "password": settings.CORR_ACCOUNTS_PASSWORD,
    }, allow_redirects=True)

    # Шаг 3: получить данные
    r = session.get(settings.CORR_ACCOUNTS_URL)
    r.raise_for_status()
    return r.json()


def get_corr_accounts():
    data = cache.get(CACHE_KEY)
    if data is not None:
        return data
    try:
        data = fetch_corr_accounts()
        cache.set(CACHE_KEY, data, CACHE_TTL)
        return data
    except Exception:
        # Для разработки дома: при недоступности CORR (нет формы логина и т.д.) отдаём заглушку
        if getattr(settings, "DEBUG", False):
            return _mock_corr_data()
        raise


def invalidate_cache():
    cache.delete(CACHE_KEY)