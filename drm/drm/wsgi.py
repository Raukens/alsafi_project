"""
WSGI config for drm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""
from dotenv import load_dotenv
load_dotenv()
import os
import sys

# wsgi.py: drm/drm/wsgi.py → нужно подняться на 3 уровня → alsafi_project/
# Это нужно для импорта services.ldap (services/ находится в корне проекта)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drm.settings')

application = get_wsgi_application()
