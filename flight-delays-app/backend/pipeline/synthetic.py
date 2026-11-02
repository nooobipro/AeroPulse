"""Генератор ДЕМОНСТРАЦИОННЫХ данных в формате Kaggle «Combined_Flights».

Все авиакомпании вымышлены, а значения задержек смоделированы случайно. Эти данные нужны только для того,
чтобы запустить и показать приложение без реального датасета; выводов о реальных перевозчиках они не дают.
"""
import argparse

import numpy as np
import pandas as pd

AIRLINES = [  # название, сдвиг логита задержки, вес (доля рейсов)
    ("Aurora Air", -0.55, 12), ("Borealis Airways", -0.20, 10), ("Cirrus Jet", 0.10, 9),
    ("Dune Airlines", 0.45, 8), ("Ember Air", -0.80, 7), ("Fjord Aviation", 0.00, 7),
    ("Glacier Air", 0.65, 6), ("Harbor Wings", -0.30, 5), ("Ion Express", 0.25, 5),
    ("Juniper Air", -0.10, 4), ("Kestrel Regional", 0.30, 4), ("Lumen Jet", -0.45, 3),
]
AIRPORTS = [  # код, город, штат
    ("ATL", "Atlanta, GA", "GA"), ("ORD", "Chicago, IL", "IL"), ("DFW", "Dallas/Fort Worth, TX", "TX"),
    ("DEN", "Denver, CO", "CO"), ("LAX", "Los Angeles, CA", "CA"), ("JFK", "New York, NY", "NY"),
    ("LAS", "Las Vegas, NV", "NV"), ("MCO", "Orlando, FL", "FL"), ("MIA", "Miami, FL", "FL"),
    ("CLT", "Charlotte, NC", "NC"), ("SEA", "Seattle, WA", "WA"), ("PHX", "Phoenix, AZ", "AZ"),
    ("EWR", "Newark, NJ", "NJ"), ("SFO", "San Francisco, CA", "CA"), ("IAH", "Houston, TX", "TX"),
    ("BOS", "Boston, MA", "MA"), ("FLL", "Fort Lauderdale, FL", "FL"), ("MSP", "Minneapolis, MN", "MN"),
    ("LGA", "New York, NY", "NY"), ("DTW", "Detroit, MI", "MI"), ("PHL", "Philadelphia, PA", "PA"),
    ("SLC", "Salt Lake City, UT", "UT"), ("BWI", "Baltimore, MD", "MD"), ("DCA", "Washington, DC", "DC"),
    ("SAN", "San Diego, CA", "CA"), ("TPA", "Tampa, FL", "FL"), ("BNA", "Nashville, TN", "TN"),
    ("AUS", "Austin, TX", "TX"), ("MDW", "Chicago, IL", "IL"), ("PDX", "Portland, OR", "OR"),
    ("HNL", "Honolulu, HI", "HI"), ("STL", "St. Louis, MO", "MO"), ("MSY", "New Orleans, LA", "LA"),
    ("OAK", "Oakland, CA", "CA"), ("RDU", "Raleigh/Durham, NC", "NC"), ("SJC", "San Jose, CA", "CA"),
    ("SMF", "Sacramento, CA", "CA"), ("MCI", "Kansas City, MO", "MO"), ("CLE", "Cleveland, OH", "OH"),
    ("PIT", "Pittsburgh, PA", "PA"),
]
MONTH_OFFSET = {1: 0.0, 2: 0.05, 3: 0.0, 4: -0.15, 5: -0.05, 6: 0.25, 7: 0.30, 8: 0.15, 9: -0.20,
                10: -0.25, 11: -0.10, 12: 0.30}
HOUR_WEIGHTS = np.array([0.4, 0.2, 0.1, 0.1, 0.4, 1.6, 4.6, 6.0, 6.2, 5.8, 5.6, 5.8, 6.0, 5.8, 5.8, 6.0,
                         6.2, 6.2, 5.8, 5.6, 4.4, 2.8, 1.4, 0.8])
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2022-07-31")


def demo_chunk(n: int, rng: np.random.Generator) -> pd.DataFrame:
    a_w = np.array([a[2] for a in AIRLINES], float)
    a_idx = rng.choice(len(AIRLINES), n, p=a_w / a_w.sum())
    p_w = 1.0 / np.arange(1, len(AIRPORTS) + 1) ** 0.8
    p_idx = rng.choice(len(AIRPORTS), n, p=p_w / p_w.sum())
    airport_off = np.random.default_rng(7).normal(0, 0.25, len(AIRPORTS))
    airline_off = np.array([a[1] for a in AIRLINES])

    days = (END - START).days + 1
    dates = START + pd.to_timedelta(rng.integers(0, days, n), unit="D")
    hour = rng.choice(24, n, p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum())
    minute = 5 * rng.integers(0, 12, n)
    duration = np.clip(rng.gamma(4.0, 30.0, n) + 35, 35, 420).round()

    month = dates.month.to_numpy()
    season = np.array([MONTH_OFFSET[m] for m in range(1, 13)])[month - 1]
    year_off = np.where(dates.year.to_numpy() == 2022, 0.15, 0.0)
    hour_eff = np.where(hour < 6, 0.15, 0.06 * (hour - 6))
    logit = -1.0 + airline_off[a_idx] + airport_off[p_idx] + hour_eff + season + year_off + 0.1 * (duration / 60 - 2)
    delayed = rng.random(n) < 1.0 / (1.0 + np.exp(-logit))
    scale = 16 + 1.2 * np.clip(hour - 6, 0, 14)
    minutes = np.ceil(1 + rng.exponential(scale, n)) * np.where(rng.random(n) < 0.03, 6, 1)
    delay = np.where(delayed, np.minimum(minutes, 2500), 0.0)

    cancelled = rng.random(n) < 0.015
    diverted = ~cancelled & (rng.random(n) < 0.0025)
    delay = np.where(cancelled | diverted, np.nan, delay)

    return pd.DataFrame({
        "FlightDate": dates.strftime("%Y-%m-%d"),
        "Airline": [AIRLINES[i][0] for i in a_idx],
        "Origin": [AIRPORTS[i][0] for i in p_idx],
        "OriginCityName": [AIRPORTS[i][1] for i in p_idx],
        "OriginState": [AIRPORTS[i][2] for i in p_idx],
        "Cancelled": cancelled,
        "Diverted": diverted,
        "CRSDepTime": (hour * 100 + minute).astype(float),
        "ArrDelayMinutes": delay,
        "CRSElapsedTime": duration,
    })


def iter_demo(rows: int, chunk_size: int = 200_000, seed: int = 20260101):
    rng = np.random.default_rng(seed)
    left = rows
    while left > 0:
        n = min(chunk_size, left)
        yield demo_chunk(n, rng)
        left -= n


def main() -> None:
    ap = argparse.ArgumentParser(description="Сгенерировать демонстрационный CSV (синтетические данные).")
    ap.add_argument("--rows", type=int, default=400_000)
    ap.add_argument("--out", default="demo_flights.csv")
    ap.add_argument("--seed", type=int, default=20260101)
    args = ap.parse_args()
    first = True
    for chunk in iter_demo(args.rows, seed=args.seed):
        chunk.to_csv(args.out, mode="w" if first else "a", header=first, index=False)
        first = False
    print(f"Записано {args.rows} строк в {args.out}")


if __name__ == "__main__":
    main()
