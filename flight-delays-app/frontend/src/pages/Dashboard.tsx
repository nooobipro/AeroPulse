import { Container, Group, Stack, Tabs, Text, Title } from '@mantine/core';
import { IconBuildingAirport, IconChartBar, IconClockHour4, IconGitCompare, IconListNumbers } from '@tabler/icons-react';
import { useSearchParams } from 'react-router-dom';
import { useFilterOptions, useKpi, useMe } from '../api/hooks';
import { AnalystToolbar } from '../components/AnalystToolbar';
import { EmptyNote, ErrorNote } from '../components/common';
import { FilterBar } from '../components/FilterBar';
import { KpiBoard } from '../components/KpiBoard';
import { useFilters } from '../filters';
import { ROLE_RANK, fmtPeriod } from '../utils/format';
import AirlinesTab from './dashboard/AirlinesTab';
import AirportsTab from './dashboard/AirportsTab';
import CategoriesTab from './dashboard/CategoriesTab';
import CompareTab from './dashboard/CompareTab';
import TimeTab from './dashboard/TimeTab';

const TABS = ['time', 'airlines', 'airports', 'categories', 'compare'];

export default function Dashboard() {
  const [filters, update, reset] = useFilters();
  const [sp, setSp] = useSearchParams();
  const { data: me } = useMe();
  const { data: opts } = useFilterOptions();
  const kpi = useKpi(filters);
  const requested = sp.get('tab') ?? 'time';
  const tab = TABS.includes(requested) ? requested : 'time';
  const isAnalyst = !!me && ROLE_RANK[me.role] >= ROLE_RANK.analyst;
  const empty = kpi.data?.flights === 0;

  const setTab = (v: string | null) =>
    setSp((prev) => { const n = new URLSearchParams(prev); n.set('tab', v ?? 'time'); return n; }, { replace: true });

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <Group justify="space-between" align="flex-end" wrap="wrap">
          <div>
            <Title order={2} className="page-title">Панель показателей</Title>
            {opts?.data && (
              <Text size="sm" c="dimmed">
                Данные: {fmtPeriod(opts.data.period_start)} — {fmtPeriod(opts.data.period_end)}; задержка считается по времени прибытия, отменённые и перенаправленные рейсы исключены.
              </Text>
            )}
          </div>
          {isAnalyst && <AnalystToolbar filters={filters} onApply={update} />}
        </Group>

        <FilterBar filters={filters} onChange={update} onReset={reset} />
        {kpi.error && <ErrorNote error={kpi.error} />}
        <KpiBoard kpi={kpi.data} filters={filters} />

        {empty ? (
          <EmptyNote>По выбранным фильтрам нет выполненных рейсов. Расширьте период, диапазон времени или уберите часть фильтров.</EmptyNote>
        ) : (
          <Tabs value={tab} onChange={setTab} keepMounted={false} color="amber.5" variant="default">
            <Tabs.List style={{ flexWrap: 'nowrap', overflowX: 'auto' }}>
              <Tabs.Tab value="time" leftSection={<IconClockHour4 size={16} />}>Время вылета</Tabs.Tab>
              <Tabs.Tab value="airlines" leftSection={<IconChartBar size={16} />}>Авиакомпании</Tabs.Tab>
              <Tabs.Tab value="airports" leftSection={<IconBuildingAirport size={16} />}>Аэропорты</Tabs.Tab>
              <Tabs.Tab value="categories" leftSection={<IconListNumbers size={16} />}>Категории задержек</Tabs.Tab>
              <Tabs.Tab value="compare" leftSection={<IconGitCompare size={16} />}>Сравнение авиакомпаний</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="time" pt="md"><TimeTab filters={filters} /></Tabs.Panel>
            <Tabs.Panel value="airlines" pt="md"><AirlinesTab filters={filters} /></Tabs.Panel>
            <Tabs.Panel value="airports" pt="md"><AirportsTab filters={filters} /></Tabs.Panel>
            <Tabs.Panel value="categories" pt="md"><CategoriesTab filters={filters} /></Tabs.Panel>
            <Tabs.Panel value="compare" pt="md"><CompareTab filters={filters} /></Tabs.Panel>
          </Tabs>
        )}
      </Stack>
    </Container>
  );
}
