"""
WSGI config for drm project.
"""
import os
import sys
from pathlib import Path

# wsgi.py находится в drm/drm/ — поднимаемся на 3 уровня до alsafi_project/
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_DRM = str(Path(__file__).resolve().parent.parent)

# Добавляем корень проекта в sys.path для импорта services
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Загружаем .env с явным путём до того, как Django инициализируется
from dotenv import load_dotenv
load_dotenv(Path(_ROOT) / ".env")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drm.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
