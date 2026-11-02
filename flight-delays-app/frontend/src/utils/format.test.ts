import { describe, expect, it } from 'vitest';
import { DASH, fmtHour, fmtInt, fmtMin, fmtP, fmtPct, fmtPeriod, fmtSigned } from './format';

const norm = (s: string) => s.replace(/\u00a0|\u202f/g, ' ');

describe('форматирование чисел', () => {
  it('целые с разделителем тысяч', () => expect(norm(fmtInt(3930204))).toBe('3 930 204'));
  it('доли в процентах с запятой', () => {
    expect(norm(fmtPct(0.372))).toBe('37,2 %');
    expect(norm(fmtPct(0.4567, 0))).toBe('46 %');
  });
  it('пустые значения — тире', () => {
    expect(fmtPct(null)).toBe(DASH);
    expect(fmtMin(undefined)).toBe(DASH);
    expect(fmtInt(null)).toBe(DASH);
  });
  it('минуты, часы, месяцы', () => {
    expect(norm(fmtMin(11.54))).toBe('11,5 мин');
    expect(fmtHour(7)).toBe('07:00');
    expect(fmtPeriod('2021-03')).toBe('март 2021');
  });
  it('p-value: очень малые значения не пишутся нулём', () => {
    expect(fmtP(0)).toBe('< 0,001');
    expect(fmtP(0.0234)).toBe('0,023');
  });
  it('знак у разностей', () => {
    expect(fmtSigned(1.5, 1)).toBe('+1,5');
    expect(fmtSigned(-0.25, 2)).toBe('-0,25');
  });
});
