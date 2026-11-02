"""Словесные оценки силы связи и размера эффекта (общепринятые ориентиры)."""


def label_spearman(rho: float) -> str:
    a = abs(rho)
    if a < 0.1:
        return "практически отсутствует"
    if a < 0.3:
        return "слабая"
    if a < 0.5:
        return "умеренная"
    if a < 0.7:
        return "заметная"
    return "сильная"


def label_cramers_v(v: float) -> str:
    """Ориентиры Коэна для V Крамера при df* = 1."""
    if v < 0.1:
        return "незначительная"
    if v < 0.3:
        return "слабая"
    if v < 0.5:
        return "умеренная"
    return "сильная"


def label_epsilon_sq(e: float) -> str:
    """Ориентиры, аналогичные η² Коэна: 0,01 / 0,06 / 0,14."""
    if e < 0.01:
        return "незначительный"
    if e < 0.06:
        return "малый"
    if e < 0.14:
        return "средний"
    return "большой"
