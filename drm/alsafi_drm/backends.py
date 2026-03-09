"""
Бэкенд аутентификации по LDAP/AD через services.ldap.verify_user.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class LDAPBackend(ModelBackend):
    """Проверка логина/пароля через LDAP; создание/обновление User по данным AD."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Для разработки дома: при DEBUG не проверять пароль, принять любой логин
        if getattr(settings, "DEBUG", False):
            login = (username or getattr(settings, "SSO_DEV_USER", None) or "dev").strip()
            user, _ = User.objects.get_or_create(
                username=login,
                defaults={"first_name": login, "email": f"{login}@local.dev"},
            )
            return user

        if not username or not password:
            return None
        try:
            from services.ldap import verify_user
            info = verify_user(username.strip(), password)
        except Exception:
            return None
        if not info:
            return None
        username = (info.get("username") or username).strip()
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
