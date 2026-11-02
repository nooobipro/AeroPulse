import { SimpleGrid, Stack } from '@mantine/core';
import { useMemo } from 'react';
import { useHeatmap, useHourly, useMonthly, usePeriods } from '../../api/hooks';
import { heatmapOption, hourlyOption, monthlyOption, periodsOption } from '../../charts/options';
import { ChartPanel, ErrorNote } from '../../components/common';
import type { Filters } from '../../filters';

export default function TimeTab({ filters }: { filters: Filters }) {
  const hourly = useHourly(filters);
  const periods = usePeriods(filters);
  const heat = useHeatmap(filters);
  const monthly = useMonthly(filters);
  const avgLabel = filters.avgMode === 'all' ? 'Средняя задержка, мин (все рейсы)' : 'Средняя задержка, мин (среди задержанных)';

  const hourlyOpt = useMemo(() => (hourly.data ? hourlyOption(hourly.data, avgLabel) : null), [hourly.data, avgLabel]);
  const periodsOpt = useMemo(() => (periods.data ? periodsOption(periods.data) : null), [periods.data]);
  const heatOpt = useMemo(() => (heat.data ? heatmapOption(heat.data) : null), [heat.data]);
  const monthlyOpt = useMemo(() => (monthly.data ? monthlyOption(monthly.data) : null), [monthly.data]);

  const error = hourly.error || periods.error || heat.error || monthly.error;
  return (
    <Stack gap="md">
      {error && <ErrorNote error={error} />}
      <ChartPanel
        title="Доля задержанных рейсов по часам вылета"
        hint="Столбцы — доля рейсов, прибывших с опозданием; линия — средняя задержка в минутах. Время местное для аэропорта вылета."
        option={hourlyOpt} loading={hourly.isFetching}
      />
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <ChartPanel
          title="Периоды суток" hint="Ночь 00–05, утро 06–11, день 12–17, вечер 18–23 ч." option={periodsOpt} loading={periods.isFetching} height={300}
        />
        <ChartPanel
          title="Динамика по месяцам" hint="Показывает сезонность: связь с временем вылета оценивается на фоне сезонных колебаний." option={monthlyOpt}
          loading={monthly.isFetching} height={300}
        />
      </SimpleGrid>
      <ChartPanel
        title="День недели и час вылета"
        hint="Чем темнее ячейка, тем выше доля задержанных рейсов. Ячейки менее чем с 30 рейсами не показаны: оценка по ним ненадёжна."
        option={heatOpt} loading={heat.isFetching} height={380}
      />
    </Stack>
  );
}
