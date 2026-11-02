"""Сопоставление столбцов исходных CSV с логическими полями конвейера.

По умолчанию поддерживаются имена из наборов Kaggle «Combined_Flights_2021/2022»
(FlightDate, Airline, Origin, CRSDepTime, ArrDelayMinutes, …) и «2015 Flight Delays» (FL_DATE, AIRLINE, …).
Если у вас другие имена — укажите их флагом --map, например: --map airline=Carrier
"""

CANDIDATES: dict[str, list[str]] = {
    "date": ["FlightDate", "FL_DATE"],
    "year": ["Year", "YEAR"],
    "month": ["Month", "MONTH"],
    "day": ["DayofMonth", "DayOfMonth", "DAY"],
    "airline": ["Airline", "AIRLINE", "Reporting_Airline", "Operating_Airline"],
    "origin": ["Origin", "ORIGIN", "ORIGIN_AIRPORT"],
    "origin_city": ["OriginCityName", "ORIGIN_CITY_NAME"],
    "origin_state": ["OriginState", "ORIGIN_STATE"],
    "sched_dep": ["CRSDepTime", "SCHEDULED_DEPARTURE", "CRS_DEP_TIME"],
    "arr_delay": ["ArrDelayMinutes", "ArrDelay", "ARRIVAL_DELAY", "ARR_DELAY"],
    "cancelled": ["Cancelled", "CANCELLED"],
    "diverted": ["Diverted", "DIVERTED"],
    "duration": ["CRSElapsedTime", "SCHEDULED_TIME", "CRS_ELAPSED_TIME"],
}
REQUIRED = ("airline", "origin", "sched_dep", "arr_delay", "cancelled", "diverted")


def resolve_columns(header: list[str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    overrides = overrides or {}
    lower = {h.lower(): h for h in header}
    cols: dict[str, str] = {}
    for key, names in CANDIDATES.items():
        if key in overrides:
            if overrides[key] not in header:
                raise ValueError(f"Столбец «{overrides[key]}» (для {key}) не найден в файле")
            cols[key] = overrides[key]
            continue
        for name in names:
            if name in header:
                cols[key] = name
                break
            if name.lower() in lower:
                cols[key] = lower[name.lower()]
                break
    missing = [k for k in REQUIRED if k not in cols]
    if "date" not in cols and not all(k in cols for k in ("year", "month", "day")):
        missing.append("date (FlightDate либо Year+Month+DayofMonth)")
    if missing:
        raise ValueError(
            f"В файле не найдены обязательные столбцы: {', '.join(missing)}. "
            f"Столбцы файла: {', '.join(header)}. Сопоставьте их флагом --map ключ=Столбец."
        )
    return cols
