"""Офлайн-конвейер: исходные CSV → очистка → агрегаты и статистика → запись в БД.

Примеры:
    python -m pipeline.run --demo                                   # демонстрационные (синтетические) данные
    python -m pipeline.run --csv Combined_Flights_2021.csv Combined_Flights_2022.csv
    python -m pipeline.run --csv flights.csv --map airline=Carrier --database-url postgresql+psycopg://...
"""
import argparse
import logging
import sys
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from app.config import settings
from app.db import Base, make_engine
from pipeline import columns, regression, stat_tests, synthetic, transform, writer

log = logging.getLogger("pipeline")
STR_FIELDS = ("airline", "origin", "origin_city", "origin_state", "cancelled", "diverted")


def iter_csv(paths: list[str], chunk_size: int, overrides: dict[str, str]) -> Iterator[tuple[pd.DataFrame, dict]]:
    for path in paths:
        header = list(pd.read_csv(path, nrows=0).columns)
        cols = columns.resolve_columns(header, overrides)
        log.info("Файл %s: найдены столбцы %s", path, cols)
        dtypes = {cols[k]: str for k in STR_FIELDS if k in cols}
        for chunk in pd.read_csv(path, usecols=sorted(set(cols.values())), chunksize=chunk_size, dtype=dtypes):
            yield chunk, cols


def iter_demo(rows: int, chunk_size: int, seed: int) -> Iterator[tuple[pd.DataFrame, dict]]:
    cols = None
    for chunk in synthetic.iter_demo(rows, chunk_size, seed):
        cols = cols or columns.resolve_columns(list(chunk.columns))
        yield chunk, cols


@dataclass
class Ingested:
    agg: pd.DataFrame
    sample: pd.DataFrame
    enc_airline: transform.Encoder
    enc_origin: transform.Encoder
    origin_meta: dict
    counters: transform.Counters


def ingest(chunks: Iterable[tuple[pd.DataFrame, dict]], sample_frac: float, seed: int, merge_every: int = 6) -> Ingested:
    enc_a, enc_o, meta, counters = transform.Encoder(), transform.Encoder(), {}, transform.Counters()
    rng = np.random.default_rng(seed)
    partials: list[pd.DataFrame] = []
    samples: list[pd.DataFrame] = []
    for i, (df, cols) in enumerate(chunks, 1):
        d = transform.prepare_chunk(df, cols, enc_a, enc_o, meta, counters)
        if not d.empty:
            partials.append(transform.aggregate_chunk(d))
            samples.append(transform.sample_chunk(d, sample_frac, rng))
            if len(partials) >= merge_every:
                partials = [transform.merge_aggregates(partials)]
        log.info("Обработано порций: %d, строк: %d", i, counters.rows_total)
    if not partials:
        raise SystemExit("В данных не найдено ни одной корректной строки. Проверьте формат файлов и --map.")
    return Ingested(transform.merge_aggregates(partials), pd.concat(samples, ignore_index=True),
                    enc_a, enc_o, meta, counters)


def run_pipeline(chunks: Iterable[tuple[pd.DataFrame, dict]], engine: Engine, *, sample_frac: float = 0.12,
                 sample_size: int = 1_200_000, seed: int = 42, source: str = "", is_demo: bool = False,
                 create_tables: bool = False) -> dict:
    t0 = time.time()
    if create_tables:
        Base.metadata.create_all(engine)
    ing = ingest(chunks, sample_frac, seed)
    c = ing.counters
    if c.completed == 0:
        raise SystemExit("Нет ни одного выполненного рейса с известной задержкой прибытия.")
    agg = transform.finalize_aggregate(ing.agg)
    sample = ing.sample if len(ing.sample) <= sample_size else ing.sample.sample(n=sample_size, random_state=seed)
    log.info("Агрегатов: %d; рейсов в выборке: %d", len(agg), len(sample))

    by_hour = agg.groupby("hour")[["flights", "delayed0"]].sum()
    observed = (by_hour["delayed0"] / by_hour["flights"]).to_dict()
    airline_names = dict(enumerate(ing.enc_airline.values))
    airport_names = dict(enumerate(ing.enc_origin.values))

    log.info("Критерии: Спирмен, хи-квадрат, Краскел–Уоллис, Данн …")
    kw, dunn = stat_tests.kruskal_and_dunn(sample)
    tests = stat_tests.spearman_tests(sample) + stat_tests.chi2_tests(agg) + kw
    for i, t in enumerate(tests):  # сквозная сортировка: Спирмен → хи-квадрат → Краскел–Уоллис
        t["sort_order"] = i
    log.info("Регрессионные модели …")
    models = regression.run_models(sample, airline_names, airport_names, observed, seed=seed)

    version = dict(
        period_start=f"{int(agg['ym'].min()) // 100}-{int(agg['ym'].min()) % 100:02d}",
        period_end=f"{int(agg['ym'].max()) // 100}-{int(agg['ym'].max()) % 100:02d}",
        rows_total=c.rows_total, rows_used=c.completed,
        airlines=int(agg["airline_id"].nunique()), airports=int(agg["origin_id"].nunique()),
        is_demo=is_demo, source=source[:500],
        notes={**c.as_dict(), "sample": {"fraction": sample_frac, "rows": int(len(sample)), "seed": seed,
                                         **models["info"]}},
    )
    writer.write_results(engine, agg=agg, airlines=ing.enc_airline.values, origins=ing.enc_origin.values,
                         origin_meta=ing.origin_meta, tests=tests, dunn=dunn, models=models, version=version)
    log.info("Готово за %.0f с. Рейсов использовано: %d из %d", time.time() - t0, c.completed, c.rows_total)
    return {"version": version, "tests": tests, "models": models, "dunn": dunn}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", nargs="+", metavar="FILE", help="один или несколько CSV с рейсами")
    src.add_argument("--demo", action="store_true", help="сгенерировать демонстрационные (синтетические) данные")
    ap.add_argument("--rows", type=int, default=400_000, help="число строк для --demo (по умолчанию 400000)")
    ap.add_argument("--database-url", default=None, help="по умолчанию берётся DATABASE_URL")
    ap.add_argument("--chunk-size", type=int, default=500_000)
    ap.add_argument("--sample-frac", type=float, default=None,
                    help="доля рейсов для выборки статистик (CSV: 0.12; демо: 1.0)")
    ap.add_argument("--sample-size", type=int, default=1_200_000, help="максимальный размер выборки")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--map", action="append", default=[], metavar="поле=Столбец",
                    help="ручное сопоставление столбцов, например airline=Carrier (можно несколько раз)")
    ap.add_argument("--create-tables", action="store_true", help="создать таблицы, если их нет (для разработки)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    overrides = dict(kv.split("=", 1) for kv in args.map)
    engine = make_engine(args.database_url or settings.database_url)
    if args.demo:
        frac = 1.0 if args.sample_frac is None else args.sample_frac
        chunks = iter_demo(args.rows, min(args.chunk_size, 200_000), args.seed)
        source = f"ДЕМО: синтетические данные, {args.rows} строк"
    else:
        frac = 0.12 if args.sample_frac is None else args.sample_frac
        chunks = iter_csv(args.csv, args.chunk_size, overrides)
        source = ", ".join(args.csv)
    run_pipeline(chunks, engine, sample_frac=frac, sample_size=args.sample_size, seed=args.seed, source=source,
                 is_demo=args.demo, create_tables=args.create_tables)


if __name__ == "__main__":
    sys.exit(main())
