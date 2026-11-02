import { BarChart, CustomChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, ToolboxComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';
import { describe, expect, it } from 'vitest';
import { fx } from '../test/helpers';
import {
  airlinesOption, airportsOption, calibrationOption, categoriesOption, compareCategoriesOption, compareHourlyOption,
  forestOption, heatmapOption, hourProbabilityOption, hourlyOption, monthlyOption, periodsOption,
} from './options';

echarts.use([BarChart, LineChart, ScatterChart, HeatmapChart, CustomChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, MarkLineComponent, ToolboxComponent, SVGRenderer]);

/** Серверный рендер ECharts в SVG: ловит ошибки конфигурации без браузера. */
function render(option: any): string {
  const chart = echarts.init(null as any, null as any, { renderer: 'svg', ssr: true, width: 900, height: 420 });
  chart.setOption(option);
  const svg = chart.renderToSVGString();
  chart.dispose();
  return svg;
}

const coefs = fx.regression.models.find((m: any) => m.code === 'logit_period').coefficients.filter((c: any) => c.grp === 'airline');

describe('графики строятся из реальных ответов API', () => {
  const cases: [string, () => any][] = [
    ['по часам вылета', () => hourlyOption(fx.hourly, 'Средняя задержка')],
    ['периоды суток', () => periodsOption(fx.periods)],
    ['тепловая карта', () => heatmapOption(fx.heatmap)],
    ['месяцы', () => monthlyOption(fx.monthly)],
    ['рейтинг авиакомпаний', () => airlinesOption(fx.airlines)],
    ['аэропорты', () => airportsOption(fx.airports)],
    ['категории', () => categoriesOption(fx.categories)],
    ['сравнение по часам', () => compareHourlyOption(fx.compare.a, fx.compare.b)],
    ['сравнение категорий', () => compareCategoriesOption(fx.compare.a, fx.compare.b)],
    ['вероятность по часам', () => hourProbabilityOption(fx.regression.hour_probability)],
    ['калибровка', () => calibrationOption(fx.regression.calibration)],
    ['отношения шансов (лог. шкала)', () => forestOption(coefs.map((c: any) => ({ label: c.label, est: c.odds_ratio, lo: c.or_ci_low, hi: c.or_ci_high })), { ref: 1, log: true, xName: 'ОШ' })],
    ['устойчивость коэффициента', () => forestOption(fx.regression.hour_stability.map((c: any) => ({ label: c.label, est: c.estimate, lo: c.ci_low, hi: c.ci_high })), { ref: 0, xName: 'мин' })],
  ];
  it.each(cases)('%s', (_name, build) => {
    const svg = render(build());
    expect(svg.startsWith('<svg')).toBe(true);
    expect(svg.length).toBeGreaterThan(1500);
  });

  it('пустые данные не ломают построение', () => {
    expect(() => render(hourlyOption([], 'x'))).not.toThrow();
    expect(() => render(heatmapOption([]))).not.toThrow();
    expect(() => render(airlinesOption([]))).not.toThrow();
    expect(() => render(forestOption([], { ref: 0, xName: '' }))).not.toThrow();
  });
});
