"""Предметные константы. Используются и приложением, и офлайн-конвейером."""

# Периоды суток по местному времени аэропорта вылета (границы — включительно).
PERIODS = [
    {"code": "night", "label": "Ночь", "hour_from": 0, "hour_to": 5},
    {"code": "morning", "label": "Утро", "hour_from": 6, "hour_to": 11},
    {"code": "day", "label": "День", "hour_from": 12, "hour_to": 17},
    {"code": "evening", "label": "Вечер", "hour_from": 18, "hour_to": 23},
]

# Порог «существенной» задержки: опоздание на 15 минут и более (стандарт FAA/BTS).
LATE_THRESHOLD_MIN = 15

# Категории задержки прибытия: (ключ, подпись). Границы (нижняя, верхняя] в минутах.
CATEGORIES = [
    ("c0", "0 минут"),
    ("c1_15", "1–15 минут"),
    ("c16_30", "16–30 минут"),
    ("c31_60", "31–60 минут"),
    ("c61_120", "61–120 минут"),
    ("c120p", "Более 120 минут"),
]

# Минимум рейсов, чтобы час учитывался при поиске «самого проблемного» времени вылета.
MIN_FLIGHTS_FOR_RANKING = 200

ROLES = ("user", "analyst", "admin")
ROLE_RANK = {"user": 1, "analyst": 2, "admin": 3}
ROLE_LABELS = {"user": "Пользователь", "analyst": "Аналитик", "admin": "Администратор"}

DAYS_OF_WEEK = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}


def period_of_hour(hour: int) -> dict:
    for p in PERIODS:
        if p["hour_from"] <= hour <= p["hour_to"]:
            return p
    raise ValueError(f"Недопустимый час: {hour}")
