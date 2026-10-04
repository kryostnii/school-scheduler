"""Глобальные константы приложения School Scheduler."""
from __future__ import annotations

MAX_LESSONS = 10
DAYS_PER_WEEK = 6
DAY_NAMES_RU = ["", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
DAY_NAMES_FULL = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
APP_NAME = "School Scheduler"
APP_VERSION = "0.1.0"
DB_FILENAME = "school.sqlite3"

ROOM_TYPES = [
    ("general", "Общий кабинет"),
    ("gym", "Спортзал"),
    ("computer", "Каб. информатики"),
    ("chemistry", "Каб. химии"),
    ("physics", "Каб. физики"),
    ("music", "Каб. музыки"),
    ("art", "Каб. ИЗО"),
]

ROOM_TYPE_LABELS = {code: label for code, label in ROOM_TYPES}
