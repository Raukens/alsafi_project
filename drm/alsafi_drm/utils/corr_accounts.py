import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.conf import settings

CACHE_KEY = "corr_accounts_data"
CACHE_TTL = 6 * 60 * 60


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
    if data:
        print("data from cache")
    if data is None:
        data = fetch_corr_accounts()
        cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def invalidate_cache():
    cache.delete(CACHE_KEY)