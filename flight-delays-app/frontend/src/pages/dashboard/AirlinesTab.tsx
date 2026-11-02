import { Paper, Stack } from '@mantine/core';
import { useMemo } from 'react';
import { useAirlines } from '../../api/hooks';
import type { AirlineRow } from '../../api/types';
import { airlinesOption, barsHeight } from '../../charts/options';
import { ChartPanel, EmptyNote, ErrorNote } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import type { Filters } from '../../filters';
import { fmtInt, fmtMin, fmtPct } from '../../utils/format';

export default function AirlinesTab({ filters }: { filters: Filters }) {
  const { data, error, isFetching } = useAirlines(filters);
  const rows = data ?? [];
  const option = useMemo(() => (data ? airlinesOption(data) : null), [data]);

  const columns: Column<AirlineRow>[] = [
    { key: 'name', header: 'Авиакомпания', render: (r) => r.name, sortValue: (r) => r.name },
    { key: 'flights', header: 'Рейсов', align: 'right', render: (r) => fmtInt(r.flights), sortValue: (r) => r.flights },
    { key: 'delayed', header: 'Задержано', align: 'right', render: (r) => fmtInt(r.delayed), sortValue: (r) => r.delayed },
    { key: 'share', header: 'Доля задержанных', align: 'right', render: (r) => <b>{fmtPct(r.share)}</b>, sortValue: (r) => r.share },
    { key: 'ci', header: '95% ДИ', align: 'right', render: (r) => `${fmtPct(r.ci_low)} – ${fmtPct(r.ci_high)}` },
    { key: 'avg', header: 'Средняя задержка', align: 'right', render: (r) => fmtMin(r.avg_delay), sortValue: (r) => r.avg_delay },
    { key: 'max', header: 'Максимум, мин', align: 'right', render: (r) => fmtInt(r.max_delay), sortValue: (r) => r.max_delay },
  ];

  return (
    <Stack gap="md">
      {error && <ErrorNote error={error} />}
      {data && rows.length === 0 && <EmptyNote>По выбранным фильтрам нет данных по авиакомпаниям.</EmptyNote>}
      <ChartPanel
        title="Рейтинг авиакомпаний по доле задержанных рейсов"
        hint="«Усы» — 95% доверительный интервал. Если интервалы двух компаний не пересекаются, различие между ними не случайно."
        option={option} height={barsHeight(rows.length)} loading={isFetching}
      />
      <Paper p="md">
        <SortableTable rows={rows} columns={columns} rowKey={(r) => r.airline_id} initialSort={{ key: 'share', dir: 'desc' }} />
      </Paper>
    </Stack>
  );
}
