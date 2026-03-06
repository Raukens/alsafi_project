"""
LDAP/AD: проверка пользователя и получение данных для авторизации в Django.
"""
import os
import sys
from pathlib import Path
from typing import Optional

from ldap3 import Server, Connection, SUBTREE, NTLM, ALL
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Параметры из .env
LDAP_SERVER = os.environ.get("LDAP_SERVER", "ldap://10.10.2.5")
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "DC=alsafibank,DC=com")
LDAP_BIND_USER = os.environ.get("LDAP_BIND_USER", "")
LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "")
LDAP_DOMAIN = os.environ.get("LDAP_DOMAIN", "alsafibank")
if not LDAP_DOMAIN and "\\" in LDAP_BIND_USER:
    LDAP_DOMAIN = LDAP_BIND_USER.split("\\", 1)[0]


def get_user_info(username: str) -> Optional[dict]:
    """
    Возвращает данные пользователя из AD по sAMAccountName (bind сервисной учёткой).
    """
    if not username or not LDAP_BIND_USER or not LDAP_BIND_PASSWORD:
        return None
    server = Server(LDAP_SERVER, get_info=ALL)
    conn = Connection(
        server, user=LDAP_BIND_USER, password=LDAP_BIND_PASSWORD,
        authentication=NTLM, auto_bind=True
    )
    try:
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(&(objectClass=user)(sAMAccountName={username}))",
            search_scope=SUBTREE,
            attributes=["sAMAccountName", "displayName", "mail", "cn", "givenName"]
        )
        if not conn.entries:
            return None
        entry = conn.entries[0]
        display = getattr(entry, "displayName", None) or getattr(entry, "cn", None) or username
        if hasattr(display, "__str__"):
            display = str(display)
        return {
            "username": str(getattr(entry, "sAMAccountName", username)),
            "display_name": display,
            "email": str(entry.mail) if getattr(entry, "mail", None) else None,
        }
    finally:
        conn.unbind()


def verify_user(username: str, password: str) -> Optional[dict]:
    """
    Проверяет логин и пароль через LDAP/AD (bind от имени пользователя).
    Возвращает словарь с данными пользователя при успехе, иначе None.
    """
    if not username or not password:
        return None
    user_dn = f"{LDAP_DOMAIN}\\{username}"
    server = Server(LDAP_SERVER, get_info=ALL)
    try:
        conn = Connection(
            server, user=user_dn, password=password,
            auto_bind=True, authentication=NTLM
        )
    except Exception:
        return None
    try:
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(&(objectClass=user)(sAMAccountName={username}))",
            search_scope=SUBTREE,
            attributes=["sAMAccountName", "displayName", "mail", "cn", "givenName"]
        )
        if not conn.entries:
            return {"username": username, "display_name": username, "email": None}
        entry = conn.entries[0]
        display = getattr(entry, "displayName", None) or getattr(entry, "cn", None) or username
        if hasattr(display, "__str__"):
            display = str(display)
        return {
            "username": str(getattr(entry, "sAMAccountName", username)),
            "display_name": display,
            "email": str(entry.mail) if getattr(entry, "mail", None) else None,
        }
    finally:
        conn.unbind()


# --- Скрипт для проверки (запуск: python -m services.ldap [sAMAccountName]) ---
if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else (LDAP_BIND_USER.split("\\")[-1] if LDAP_BIND_USER else None)
    if not username:
        print("Укажите имя пользователя: python -m services.ldap r.kumash")
        sys.exit(1)
    info = get_user_info(username)
    print("get_user_info:", info)