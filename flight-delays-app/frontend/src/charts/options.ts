import type { EChartsCoreOption } from 'echarts/core';
import type { AirlineRow, AirportRow, CategoryRow, CompareSide, HeatCell, HourRow, MonthRow, PeriodRow, Regression } from '../api/types';
import { COLORS } from '../theme';
import { DOW, fmtHour, fmtInt, fmtMin, fmtNum, fmtPct, fmtPeriod, round } from '../utils/format';

/* eslint-disable @typescript-eslint/no-explicit-any */
type P = any;

const FONT = '"Fira Sans", system-ui, sans-serif';
const toolbox = { right: 8, top: 0, feature: { saveAsImage: { title: 'Сохранить как PNG', name: 'график', pixelRatio: 2 } } };
const axisLabel = { color: COLORS.muted, fontFamily: FONT };
const axisLabelAll = { ...axisLabel, interval: 0, width: 86, overflow: 'break' as const };
const grid = { left: 8, right: 16, top: 44, bottom: 36, containLabel: true };
const base = (): EChartsCoreOption => ({ textStyle: { fontFamily: FONT }, animationDuration: 300, toolbox, grid });

/** Усы доверительного интервала для горизонтальных диаграмм: данные — [индекс категории, нижняя, верхняя]. */
function whiskers(data: [number, number, number][]): P {
  return {
    type: 'custom', silent: true, z: 5, tooltip: { show: false }, data, encode: { x: [1, 2], y: 0 },
    renderItem: (_: P, api: P) => {
      const y = api.value(0);
      const lo = api.coord([api.value(1), y]);
      const hi = api.coord([api.value(2), y]);
      const h = 5;
      const style = { stroke: COLORS.ink, lineWidth: 1.4 };
      return {
        type: 'group',
        children: [
          { type: 'line', shape: { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1] }, style },
          { type: 'line', shape: { x1: lo[0], y1: lo[1] - h, x2: lo[0], y2: lo[1] + h }, style },
          { type: 'line', shape: { x1: hi[0], y1: hi[1] - h, x2: hi[0], y2: hi[1] + h }, style },
        ],
      };
    },
  };
}

export const barsHeight = (n: number, row = 26) => Math.max(200, n * row + 84);

// ───────── Время вылета ─────────
export function hourlyOption(rows: HourRow[], avgLabel: string): EChartsCoreOption {
  return {
    ...base(),
    legend: { top: 0, left: 0, textStyle: { color: COLORS.muted }, data: ['Доля задержанных', avgLabel] },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps: P) => {
        const r = rows[ps[0].dataIndex];
        return `<b>${fmtHour(r.hour)}</b><br/>Доля задержанных: <b>${fmtPct(r.share)}</b><br/>Рейсов: ${fmtInt(r.flights)}<br/>${avgLabel}: ${fmtMin(r.avg_delay)}`;
      },
    },
    xAxis: { type: 'category', data: rows.map((r) => String(r.hour).padStart(2, '0')), name: 'Час вылета (местное время)', nameLocation: 'middle', nameGap: 28, axisLabel },
    yAxis: [
      { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
      { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} мин' }, splitLine: { show: false } },
    ],
    series: [
      { name: 'Доля задержанных', type: 'bar', barMaxWidth: 22, itemStyle: { color: COLORS.amber }, data: rows.map((r) => (r.share == null ? null : round(r.share * 100))) },
      { name: avgLabel, type: 'line', yAxisIndex: 1, symbolSize: 6, color: COLORS.board, lineStyle: { width: 2 }, data: rows.map((r) => (r.avg_delay == null ? null : round(r.avg_delay))) },
    ],
  };
}

export function periodsOption(rows: PeriodRow[]): EChartsCoreOption {
  const data = rows.filter((r) => r.share != null);
  return {
    ...base(),
    tooltip: {
      trigger: 'item',
      formatter: (p: P) => {
        const r = data[p.dataIndex];
        return `<b>${r.label}</b> (${fmtHour(r.hour_from)}–${fmtHour(r.hour_to)})<br/>Доля: <b>${fmtPct(r.share)}</b>, 95% ДИ ${fmtPct(r.ci_low)} – ${fmtPct(r.ci_high)}<br/>Рейсов: ${fmtInt(r.flights)}`;
      },
    },
    xAxis: { type: 'category', data: data.map((r) => `${r.label}\n${fmtHour(r.hour_from)}–${fmtHour(r.hour_to)}`), axisLabel },
    yAxis: { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [{
      type: 'bar', barMaxWidth: 56, itemStyle: { color: COLORS.amber },
      label: { show: true, position: 'top', fontFamily: FONT, fontWeight: 600, formatter: (p: P) => `${fmtNum(p.value, 1)} %` },
      data: data.map((r) => round((r.share ?? 0) * 100)),
    }],
  };
}

export function heatmapOption(cells: HeatCell[]): EChartsCoreOption {
  const ok = cells.filter((c) => c.reliable && c.share != null);
  const values = ok.map((c) => (c.share as number) * 100);
  const min = values.length ? Math.floor(Math.min(...values)) : 0;
  const max = values.length ? Math.ceil(Math.max(...values)) : 100;
  return {
    ...base(),
    grid: { left: 8, right: 16, top: 36, bottom: 64, containLabel: true },
    tooltip: {
      formatter: (p: P) => {
        const [h, d, share] = p.value;
        const c = ok.find((x) => x.hour === h && x.dow === d + 1);
        return `${DOW[d]}, ${fmtHour(h)}<br/>Доля задержанных: <b>${fmtNum(share, 1)} %</b><br/>Рейсов: ${fmtInt(c?.flights)}`;
      },
    },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0')), splitArea: { show: true }, axisLabel, name: 'Час вылета', nameLocation: 'middle', nameGap: 26 },
    yAxis: { type: 'category', data: DOW, inverse: true, splitArea: { show: true }, axisLabel },
    visualMap: {
      min, max, calculable: false, orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 14, itemHeight: 200,
      text: [`${max} %`, `${min} %`], textStyle: { color: COLORS.muted }, inRange: { color: ['#E8F1EF', '#F7D774', '#E4572E'] },
    },
    series: [{ type: 'heatmap', data: ok.map((c) => [c.hour, c.dow - 1, round((c.share as number) * 100)]), emphasis: { itemStyle: { borderColor: COLORS.ink, borderWidth: 1 } }, itemStyle: { borderColor: '#fff', borderWidth: 1 } }],
  };
}

export function monthlyOption(rows: MonthRow[]): EChartsCoreOption {
  return {
    ...base(),
    tooltip: {
      trigger: 'axis',
      formatter: (ps: P) => {
        const r = rows[ps[0].dataIndex];
        return `<b>${fmtPeriod(r.period)}</b><br/>Доля задержанных: <b>${fmtPct(r.share)}</b><br/>Рейсов: ${fmtInt(r.flights)}`;
      },
    },
    xAxis: { type: 'category', data: rows.map((r) => r.period), axisLabel: { ...axisLabel, hideOverlap: true } },
    yAxis: { type: 'value', scale: true, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [{ type: 'line', symbolSize: 6, color: COLORS.amberDeep, lineStyle: { width: 2.5 }, areaStyle: { color: 'rgba(245,179,1,0.16)' }, data: rows.map((r) => round((r.share ?? 0) * 100)) }],
  };
}

// ───────── Авиакомпании и аэропорты ─────────
function rankingOption(items: { label: string; row: AirlineRow | AirportRow }[], xName: string): EChartsCoreOption {
  const labels = items.map((i) => i.label);
  return {
    ...base(),
    grid: { left: 8, right: 24, top: 40, bottom: 40, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: P) => {
        const r = items[p.dataIndex]?.row;
        return r ? `<b>${items[p.dataIndex].label}</b><br/>Доля задержанных: <b>${fmtPct(r.share)}</b><br/>95% ДИ: ${fmtPct(r.ci_low)} – ${fmtPct(r.ci_high)}<br/>Рейсов: ${fmtInt(r.flights)}<br/>Средняя задержка: ${fmtMin(r.avg_delay)}` : '';
      },
    },
    xAxis: { type: 'value', min: 0, name: xName, nameLocation: 'middle', nameGap: 26, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    yAxis: { type: 'category', inverse: true, data: labels, axisLabel: { ...axisLabel, width: 170, overflow: 'truncate' } },
    series: [
      { type: 'bar', barMaxWidth: 16, itemStyle: { color: COLORS.amber }, data: items.map((i) => round((i.row.share ?? 0) * 100)) },
      whiskers(items.map((i, k) => [k, round((i.row.ci_low ?? 0) * 100, 2), round((i.row.ci_high ?? 0) * 100, 2)] as [number, number, number])),
    ],
  };
}

export const airlinesOption = (rows: AirlineRow[]) =>
  rankingOption(rows.map((r) => ({ label: r.name, row: r })), 'Доля задержанных рейсов, % (с 95% доверительным интервалом)');
export const airportsOption = (rows: AirportRow[]) =>
  rankingOption(rows.map((r) => ({ label: `${r.code} — ${r.city || r.name}`, row: r })), 'Доля задержанных рейсов, % (с 95% доверительным интервалом)');

export function categoriesOption(rows: CategoryRow[]): EChartsCoreOption {
  const colors = [COLORS.green, '#F9D56E', COLORS.amber, '#E89A0C', '#D2691E', COLORS.red];
  return {
    ...base(),
    tooltip: { trigger: 'item', formatter: (p: P) => `<b>${rows[p.dataIndex].label}</b><br/>Рейсов: ${fmtInt(rows[p.dataIndex].flights)}<br/>Доля: ${fmtPct(rows[p.dataIndex].share, 2)}` },
    xAxis: { type: 'category', data: rows.map((r) => r.label), axisLabel: axisLabelAll },
    yAxis: { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [{
      type: 'bar', barMaxWidth: 56,
      label: { show: true, position: 'top', fontFamily: FONT, fontWeight: 600, formatter: (p: P) => `${fmtNum(p.value, 1)} %` },
      data: rows.map((r, i) => ({ value: round((r.share ?? 0) * 100), itemStyle: { color: colors[i] } })),
    }],
  };
}

// ───────── Сравнение двух авиакомпаний ─────────
const SIDE_COLORS = [COLORS.amberDeep, COLORS.board];

export function compareHourlyOption(a: CompareSide, b: CompareSide): EChartsCoreOption {
  const hours = [...new Set([...a.hourly, ...b.hourly].map((r) => r.hour))].sort((x, y) => x - y);
  const series = (s: CompareSide, i: number) => ({
    name: s.name, type: 'line', symbolSize: 6, color: SIDE_COLORS[i], lineStyle: { width: 2.5 },
    data: hours.map((h) => { const r = s.hourly.find((x) => x.hour === h); return r?.share == null ? null : round(r.share * 100); }),
  });
  return {
    ...base(),
    legend: { top: 0, left: 0, textStyle: { color: COLORS.muted } },
    tooltip: { trigger: 'axis', valueFormatter: (v: P) => (v == null ? '—' : `${fmtNum(v, 1)} %`) },
    xAxis: { type: 'category', data: hours.map((h) => String(h).padStart(2, '0')), name: 'Час вылета', nameLocation: 'middle', nameGap: 28, axisLabel },
    yAxis: { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [series(a, 0), series(b, 1)],
  };
}

export function compareCategoriesOption(a: CompareSide, b: CompareSide): EChartsCoreOption {
  const series = (s: CompareSide, i: number) => ({
    name: s.name, type: 'bar', barMaxWidth: 28, itemStyle: { color: SIDE_COLORS[i] },
    data: s.categories.map((c) => round((c.share ?? 0) * 100)),
  });
  return {
    ...base(),
    legend: { top: 0, left: 0, textStyle: { color: COLORS.muted } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: P) => `${fmtNum(v, 1)} %` },
    xAxis: { type: 'category', data: a.categories.map((c) => c.label), axisLabel: axisLabelAll },
    yAxis: { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [series(a, 0), series(b, 1)],
  };
}

// ───────── Методы анализа ─────────
export interface ForestRow { label: string; est: number; lo: number | null; hi: number | null }

/** Точки с доверительными интервалами («лесной график»). Для отношений шансов используйте log=true и ref=1. */
export function forestOption(rows: ForestRow[], o: { ref: number; xName: string; log?: boolean; digits?: 1 | 2 | 3 }): EChartsCoreOption {
  const digits = o.digits ?? 2;
  const ci = rows.map((r, i) => [i, r.lo, r.hi] as [number, number | null, number | null]).filter((r) => r[1] != null && r[2] != null) as [number, number, number][];
  return {
    ...base(),
    grid: { left: 8, right: 28, top: 28, bottom: 44, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: P) => {
        const r = rows[p.dataIndex];
        return `<b>${r.label}</b><br/>${fmtNum(r.est, digits)}${r.lo != null && r.hi != null ? ` (95% ДИ ${fmtNum(r.lo, digits)} – ${fmtNum(r.hi, digits)})` : ''}`;
      },
    },
    xAxis: { type: o.log ? 'log' : 'value', scale: true, name: o.xName, nameLocation: 'middle', nameGap: 28, axisLabel, splitLine: { lineStyle: { color: COLORS.line } } },
    yAxis: { type: 'category', inverse: true, data: rows.map((r) => r.label), axisLabel: { ...axisLabel, width: 190, overflow: 'truncate' } },
    series: [
      {
        type: 'scatter', symbol: 'diamond', symbolSize: 11, itemStyle: { color: COLORS.amberDeep, borderColor: COLORS.ink, borderWidth: 1 }, z: 6,
        data: rows.map((r, i) => [r.est, i]),
        markLine: { silent: true, symbol: 'none', label: { show: false }, lineStyle: { color: COLORS.red, type: 'dashed', width: 1.4 }, data: [{ xAxis: o.ref }] },
      },
      whiskers(ci),
    ],
  };
}

export function hourProbabilityOption(hp: NonNullable<Regression['hour_probability']>): EChartsCoreOption {
  return {
    ...base(),
    legend: { top: 0, left: 0, textStyle: { color: COLORS.muted } },
    tooltip: { trigger: 'axis', valueFormatter: (v: P) => (v == null ? '—' : `${fmtNum(v, 1)} %`) },
    xAxis: { type: 'category', data: hp.hours.map((h) => String(h).padStart(2, '0')), name: 'Час вылета', nameLocation: 'middle', nameGap: 28, axisLabel },
    yAxis: { type: 'value', min: 0, axisLabel: { ...axisLabel, formatter: '{value} %' }, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [
      { name: 'Наблюдаемая доля', type: 'line', symbolSize: 5, color: COLORS.board, lineStyle: { width: 2, type: 'dashed' }, data: hp.observed.map((v) => (v == null ? null : round(v * 100))) },
      { name: 'При одинаковом составе рейсов (модель)', type: 'line', symbolSize: 6, color: COLORS.amberDeep, lineStyle: { width: 2.5 }, data: hp.adjusted.map((v) => round(v * 100)) },
    ],
  };
}

export function calibrationOption(bins: NonNullable<Regression['calibration']>): EChartsCoreOption {
  const max = Math.ceil(Math.max(...bins.map((b) => Math.max(b.predicted, b.observed))) * 20) * 5;
  return {
    ...base(),
    grid: { left: 8, right: 24, top: 52, bottom: 48, containLabel: true },
    tooltip: { formatter: (p: P) => `Группа ${bins[p.dataIndex]?.bin ?? ''}<br/>Предсказано: ${fmtNum(p.value[0], 1)} %<br/>Фактически: ${fmtNum(p.value[1], 1)} %` },
    xAxis: { type: 'value', min: 0, max, name: 'Предсказанная вероятность, %', nameLocation: 'middle', nameGap: 28, axisLabel, splitLine: { lineStyle: { color: COLORS.line } } },
    yAxis: { type: 'value', min: 0, max, name: 'Фактическая доля, %', nameTextStyle: { align: 'left' }, axisLabel, splitLine: { lineStyle: { color: COLORS.line } } },
    series: [
      { type: 'line', silent: true, symbol: 'none', lineStyle: { color: COLORS.muted, type: 'dashed', width: 1.2 }, data: [[0, 0], [max, max]] },
      { type: 'scatter', symbolSize: 10, itemStyle: { color: COLORS.amberDeep, borderColor: COLORS.ink }, data: bins.map((b) => [round(b.predicted * 100), round(b.observed * 100)]) },
    ],
  };
}
