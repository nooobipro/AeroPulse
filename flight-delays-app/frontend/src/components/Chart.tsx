import ReactEChartsCore from 'echarts-for-react/lib/core';
import { BarChart, CustomChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  GridComponent, LegendComponent, MarkLineComponent, ToolboxComponent, TooltipComponent, VisualMapComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { Skeleton } from '@mantine/core';

echarts.use([
  BarChart, LineChart, ScatterChart, HeatmapChart, CustomChart,
  GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, MarkLineComponent, ToolboxComponent,
  CanvasRenderer,
]);

export function Chart({ option, height = 320, loading = false }: { option: EChartsCoreOption | null; height?: number; loading?: boolean }) {
  if (!option) return <Skeleton height={height} />;
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      showLoading={loading}
      loadingOption={{ text: '', color: '#C98A00', maskColor: 'rgba(255,255,255,0.6)' }}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
}
