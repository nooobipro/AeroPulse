import { Group, Input, NumberInput, Paper, SegmentedControl, Select, Stack } from '@mantine/core';
import { useMemo, useState } from 'react';
import { useAirports } from '../../api/hooks';
import type { AirportRow } from '../../api/types';
import { airportsOption, barsHeight } from '../../charts/options';
import { ChartPanel, EmptyNote, ErrorNote } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import type { Filters } from '../../filters';
import { fmtInt, fmtMin, fmtPct } from '../../utils/format';

const MODES: Record<string, { sort: string; order: string }> = {
  worst: { sort: 'share', order: 'desc' },
  best: { sort: 'share', order: 'asc' },
  busiest: { sort: 'flights', order: 'desc' },
};

export default function AirportsTab({ filters }: { filters: Filters }) {
  const [mode, setMode] = useState('worst');
  const [minFlights, setMinFlights] = useState<number>(500);
  const [limit, setLimit] = useState<string>('20');
  const { data, error, isFetching } = useAirports(filters, MODES[mode].sort, MODES[mode].order, minFlights || 1, Number(limit));
  const rows = data ?? [];
  const option = useMemo(() => (data ? airportsOption(data) : null), [data]);

  const columns: Column<AirportRow>[] = [
    { key: 'code', header: 'Код', render: (r) => <b>{r.code}</b>, sortValue: (r) => r.code },
    { key: 'city', header: 'Город', render: (r) => r.city || r.name, sortValue: (r) => r.city || r.name },
    { key: 'flights', header: 'Рейсов', align: 'right', render: (r) => fmtInt(r.flights), sortValue: (r) => r.flights },
    { key: 'share', header: 'Доля задержанных', align: 'right', render: (r) => <b>{fmtPct(r.share)}</b>, sortValue: (r) => r.share },
    { key: 'ci', header: '95% ДИ', align: 'right', render: (r) => `${fmtPct(r.ci_low)} – ${fmtPct(r.ci_high)}` },
    { key: 'avg', header: 'Средняя задержка', align: 'right', render: (r) => fmtMin(r.avg_delay), sortValue: (r) => r.avg_delay },
  ];

  return (
    <Stack gap="md">
      <Paper p="md">
        <Group align="flex-end" gap="lg" wrap="wrap">
          <Input.Wrapper label="Показать">
            <SegmentedControl
              size="xs" value={mode} onChange={setMode}
              data={[{ value: 'worst', label: 'Наибольшая доля задержек' }, { value: 'best', label: 'Наименьшая доля' }, { value: 'busiest', label: 'Больше всего рейсов' }]}
            />
          </Input.Wrapper>
          <NumberInput
            label="Минимум рейсов" description="Малые выборки дают случайные доли" min={1} max={1_000_000} step={100} w={210}
            value={minFlights} onChange={(v) => setMinFlights(typeof v === 'number' ? v : 1)} thousandSeparator=" "
          />
          <Select label="Число аэропортов" data={['10', '20', '50', '100']} value={limit} onChange={(v) => setLimit(v ?? '20')} allowDeselect={false} w={150} />
        </Group>
      </Paper>
      {error && <ErrorNote error={error} />}
      {data && rows.length === 0 && <EmptyNote>Нет аэропортов, удовлетворяющих условиям. Уменьшите минимальное число рейсов или ослабьте фильтры.</EmptyNote>}
      <ChartPanel
        title="Аэропорты вылета" hint="Доля задержанных рейсов, отправляющихся из аэропорта (с 95% доверительным интервалом)."
        option={option} height={barsHeight(rows.length)} loading={isFetching}
      />
      <Paper p="md"><SortableTable rows={rows} columns={columns} rowKey={(r) => r.airport_id} initialSort={{ key: MODES[mode].sort === 'flights' ? 'flights' : 'share', dir: MODES[mode].order as 'asc' | 'desc' }} key={mode} /></Paper>
    </Stack>
  );
}
