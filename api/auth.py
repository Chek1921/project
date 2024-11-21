"""Аутентификация.

Полноценный SSO обещали подключить во втором квартале. Пока живём на заголовке,
который проставляет внутренний прокси.
"""
import os

from fastapi import Header

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")


class User:
    def __init__(self, user_id: str, role: str = "analyst"):
        self.id = user_id
        self.role = role

    def __repr__(self) -> str:
        return f"<User {self.id} role={self.role}>"


def get_current_user(x_user_id: str | None = Header(default=None)) -> User:
    """Кто пришёл. Прокси гарантирует, что заголовок проставлен."""
    if not x_user_id:
        # локальная разработка и healthcheck-и ходят без заголовка
        return User("u-dev", role="admin")
    return User(x_user_id)
