"""Мелкие общие функции: время, доверительные интервалы, проверка пароля."""
import math
import re
from datetime import datetime, timezone

Z95 = 1.959963984540054


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """SQLite возвращает «наивные» даты; считаем их UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float | None, float | None]:
    """Доверительный интервал Уилсона для доли k/n."""
    if n <= 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def two_proportion_test(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Разность долей p1 - p2, её 95% ДИ (Вальд) и p-value z-критерия (объединённая доля)."""
    p1, p2 = k1 / n1, k2 / n2
    diff = p1 - p2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    pooled = (k1 + k2) / (n1 + n2)
    se0 = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = diff / se0 if se0 > 0 else 0.0
    return {
        "diff": diff,
        "ci_low": diff - Z95 * se,
        "ci_high": diff + Z95 * se,
        "p_value": math.erfc(abs(z) / math.sqrt(2)),
    }


def validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов")
    if len(value) > 128:
        raise ValueError("Пароль не должен быть длиннее 128 символов")
    if not re.search(r"[^\W\d_]", value) or not re.search(r"\d", value):
        raise ValueError("Пароль должен содержать и буквы, и цифры")
    return value
