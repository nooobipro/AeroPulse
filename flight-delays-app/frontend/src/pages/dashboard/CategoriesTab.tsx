import { Paper, Stack } from '@mantine/core';
import { useMemo } from 'react';
import { useCategories } from '../../api/hooks';
import type { CategoryRow } from '../../api/types';
import { categoriesOption } from '../../charts/options';
import { ChartPanel, ErrorNote } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import type { Filters } from '../../filters';
import { fmtInt, fmtPct } from '../../utils/format';

export default function CategoriesTab({ filters }: { filters: Filters }) {
  const { data, error, isFetching } = useCategories(filters);
  const option = useMemo(() => (data ? categoriesOption(data) : null), [data]);
  const columns: Column<CategoryRow>[] = [
    { key: 'label', header: 'Категория задержки прибытия', render: (r) => r.label },
    { key: 'flights', header: 'Рейсов', align: 'right', render: (r) => fmtInt(r.flights) },
    { key: 'share', header: 'Доля рейсов', align: 'right', render: (r) => <b>{fmtPct(r.share, 2)}</b> },
  ];
  return (
    <Stack gap="md">
      {error && <ErrorNote error={error} />}
      <ChartPanel
        title="Распределение рейсов по категориям задержки"
        hint="Категория «0 минут» включает рейсы, прибывшие вовремя или раньше расписания. Крупные задержки редки, но именно они создают основную нагрузку на авиакомпанию."
        option={option} height={340} loading={isFetching}
      />
      <Paper p="md"><SortableTable rows={data ?? []} columns={columns} rowKey={(r) => r.key} minWidth={480} /></Paper>
    </Stack>
  );
}
