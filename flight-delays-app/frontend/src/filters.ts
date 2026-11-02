import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { SavedParams } from './api/types';

export interface Filters {
  airlines: number[];
  airports: number[];
  periodFrom: string | null;
  periodTo: string | null;
  hourFrom: number;
  hourTo: number;
  threshold: 0 | 15;
  avgMode: 'all' | 'delayed';
}

export const DEFAULT_FILTERS: Filters = {
  airlines: [], airports: [], periodFrom: null, periodTo: null, hourFrom: 0, hourTo: 23, threshold: 0, avgMode: 'all',
};

const PERIOD_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
const ids = (values: string[]) =>
  [...new Set(values.map(Number).filter((n) => Number.isInteger(n) && n > 0))].sort((a, b) => a - b);
const hour = (v: string | null, fallback: number) => {
  const n = Number(v);
  return v !== null && Number.isInteger(n) && n >= 0 && n <= 23 ? n : fallback;
};

/** Фильтры → параметры запроса. Имена совпадают с API, поэтому те же параметры годятся и для адресной строки. */
export function filtersToParams(f: Filters, opts: { omitAirlines?: boolean } = {}): URLSearchParams {
  const sp = new URLSearchParams();
  if (!opts.omitAirlines) f.airlines.forEach((id) => sp.append('airline_id', String(id)));
  f.airports.forEach((id) => sp.append('airport_id', String(id)));
  if (f.periodFrom) sp.set('period_from', f.periodFrom);
  if (f.periodTo) sp.set('period_to', f.periodTo);
  if (f.hourFrom !== 0) sp.set('hour_from', String(f.hourFrom));
  if (f.hourTo !== 23) sp.set('hour_to', String(f.hourTo));
  if (f.threshold !== 0) sp.set('threshold', String(f.threshold));
  if (f.avgMode !== 'all') sp.set('avg_mode', f.avgMode);
  return sp;
}

export function filtersFromParams(sp: URLSearchParams): Filters {
  const from = hour(sp.get('hour_from'), 0);
  const to = hour(sp.get('hour_to'), 23);
  const pf = sp.get('period_from');
  const pt = sp.get('period_to');
  return {
    airlines: ids(sp.getAll('airline_id')),
    airports: ids(sp.getAll('airport_id')),
    periodFrom: pf && PERIOD_RE.test(pf) ? pf : null,
    periodTo: pt && PERIOD_RE.test(pt) ? pt : null,
    hourFrom: Math.min(from, to),
    hourTo: Math.max(from, to),
    threshold: sp.get('threshold') === '15' ? 15 : 0,
    avgMode: sp.get('avg_mode') === 'delayed' ? 'delayed' : 'all',
  };
}

export const filtersToSaved = (f: Filters): SavedParams => ({
  airline_id: f.airlines, airport_id: f.airports, period_from: f.periodFrom, period_to: f.periodTo,
  hour_from: f.hourFrom, hour_to: f.hourTo, threshold: f.threshold, avg_mode: f.avgMode,
});

export const filtersFromSaved = (p: Partial<SavedParams>): Filters => ({
  airlines: p.airline_id ?? [], airports: p.airport_id ?? [], periodFrom: p.period_from ?? null,
  periodTo: p.period_to ?? null, hourFrom: p.hour_from ?? 0, hourTo: p.hour_to ?? 23,
  threshold: p.threshold === 15 ? 15 : 0, avgMode: p.avg_mode === 'delayed' ? 'delayed' : 'all',
});

export const isDefault = (f: Filters) => filtersToParams(f).toString() === '';

/** Фильтры хранятся в адресной строке: ссылкой на панель можно поделиться, работает кнопка «Назад». */
export function useFilters(): [Filters, (patch: Partial<Filters>) => void, () => void] {
  const [sp, setSp] = useSearchParams();
  const key = sp.toString();
  const filters = useMemo(() => filtersFromParams(new URLSearchParams(key)), [key]);
  const write = (next: Filters) => {
    const params = filtersToParams(next);
    const tab = sp.get('tab');
    if (tab) params.set('tab', tab);
    setSp(params, { replace: true });
  };
  return [filters, (patch) => write({ ...filters, ...patch }), () => write(DEFAULT_FILTERS)];
}
