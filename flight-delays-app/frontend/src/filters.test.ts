import { describe, expect, it } from 'vitest';
import { DEFAULT_FILTERS, filtersFromParams, filtersFromSaved, filtersToParams, filtersToSaved, isDefault } from './filters';

describe('фильтры ↔ адресная строка', () => {
  it('значения по умолчанию не попадают в URL', () => {
    expect(filtersToParams(DEFAULT_FILTERS).toString()).toBe('');
    expect(isDefault(DEFAULT_FILTERS)).toBe(true);
  });

  it('туда и обратно без потерь', () => {
    const f = { airlines: [3, 1], airports: [7], periodFrom: '2021-03', periodTo: '2022-01', hourFrom: 6, hourTo: 12, threshold: 15 as const, avgMode: 'delayed' as const };
    const back = filtersFromParams(filtersToParams(f));
    expect(back).toEqual({ ...f, airlines: [3, 1].sort() });
    expect(filtersToParams(f).getAll('airline_id')).toEqual(['3', '1']);
  });

  it('мусор в URL игнорируется или нормализуется', () => {
    const f = filtersFromParams(new URLSearchParams('airline_id=abc&airline_id=-4&airline_id=5&airline_id=5&period_from=2021-13&hour_from=20&hour_to=8&threshold=99&avg_mode=x'));
    expect(f.airlines).toEqual([5]);
    expect(f.periodFrom).toBeNull();
    expect([f.hourFrom, f.hourTo]).toEqual([8, 20]);
    expect(f.threshold).toBe(0);
    expect(f.avgMode).toBe('all');
  });

  it('можно исключить авиакомпании (для сравнения двух компаний)', () => {
    expect(filtersToParams({ ...DEFAULT_FILTERS, airlines: [1, 2], threshold: 15 }, { omitAirlines: true }).toString()).toBe('threshold=15');
  });

  it('сохранённые наборы совместимы с форматом API', () => {
    const f = { ...DEFAULT_FILTERS, airlines: [2], hourFrom: 5, threshold: 15 as const };
    const saved = filtersToSaved(f);
    expect(saved).toMatchObject({ airline_id: [2], hour_from: 5, hour_to: 23, threshold: 15, avg_mode: 'all' });
    expect(filtersFromSaved(saved)).toEqual(f);
    expect(filtersFromSaved({})).toEqual(DEFAULT_FILTERS);
  });
});
