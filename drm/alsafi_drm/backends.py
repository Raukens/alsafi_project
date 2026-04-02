"""
Бэкенд аутентификации по LDAP/AD через services.ldap.verify_user.
"""
import logging
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)
User = get_user_model()


class LDAPBackend(ModelBackend):
    """Проверка логина/пароля через LDAP; создание/обновление User по данным AD."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Гарантируем, что корень проекта есть в sys.path (нужно при запуске через wsgi/gunicorn)
        project_root = str(Path(settings.BASE_DIR).parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from services.ldap import verify_user
            info = verify_user(username.strip(), password)
        except Exception as e:
            logger.error("Ошибка при вызове verify_user для '%s': %s", username, e, exc_info=True)
            return None
        if not info:
            logger.warning("verify_user вернул None для пользователя '%s'", username)
            return None
        username = (info.get("username") or username).strip()

        # Список читается из .env напрямую при каждом входе (без перезапуска сервера)
        env_path = Path(settings.BASE_DIR).parent / ".env"
        env_values = dotenv_values(env_path)
        raw = env_values.get("ALLOWED_LDAP_USERNAMES", "")
        allowed = [u.strip().lower() for u in raw.split(",") if u.strip()]
        if allowed and username.lower() not in allowed:
            return None
        display_name = (info.get("display_name") or username)[:150]
        email = (info.get("email") or "")[:254]
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": display_name, "email": email},
        )
        if not created:
            user.first_name = display_name
            user.email = email
            user.save(update_fields=["first_name", "email"])
        return user
