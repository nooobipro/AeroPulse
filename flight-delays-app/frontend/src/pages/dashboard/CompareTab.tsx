import { Alert, Group, Paper, Select, SimpleGrid, Stack, Table, Text } from '@mantine/core';
import { useEffect, useMemo, useState } from 'react';
import { useAirlines, useCompare, useFilterOptions } from '../../api/hooks';
import type { Kpi } from '../../api/types';
import { compareCategoriesOption, compareHourlyOption } from '../../charts/options';
import { ChartPanel, EmptyNote, ErrorNote } from '../../components/common';
import type { Filters } from '../../filters';
import { fmtHour, fmtInt, fmtMin, fmtNum, fmtP, fmtPct, fmtSigned } from '../../utils/format';

const worstHour = (k: Kpi) => (k.worst_hour ? `${fmtHour(k.worst_hour.hour)} (${fmtPct(k.worst_hour.share)})` : '—');

export default function CompareTab({ filters }: { filters: Filters }) {
  const { data: opts } = useFilterOptions();
  const ranking = useAirlines({ ...filters, airlines: [] });
  const [a, setA] = useState<string | null>(null);
  const [b, setB] = useState<string | null>(null);

  // Для наглядности сразу предлагаем самую «опаздывающую» и самую пунктуальную компании
  useEffect(() => {
    const r = ranking.data;
    if (r && r.length >= 2 && a === null && b === null) { setA(String(r[0].airline_id)); setB(String(r[r.length - 1].airline_id)); }
  }, [ranking.data, a, b]);

  const { data, error, isFetching } = useCompare(filters, a ? Number(a) : null, b ? Number(b) : null);
  const options = useMemo(() => (opts?.airlines ?? []).map((x) => ({ value: String(x.id), label: x.name })), [opts]);
  const hourlyOpt = useMemo(() => (data ? compareHourlyOption(data.a, data.b) : null), [data]);
  const catOpt = useMemo(() => (data ? compareCategoriesOption(data.a, data.b) : null), [data]);

  return (
    <Stack gap="md">
      <Paper p="md">
        <Group align="flex-end" gap="md" wrap="wrap">
          <Select label="Авиакомпания A" data={options} value={a} onChange={setA} searchable placeholder="Выберите" w={260} />
          <Select label="Авиакомпания B" data={options} value={b} onChange={setB} searchable placeholder="Выберите" w={260} />
          <Text size="sm" c="dimmed" maw={420}>Фильтры аэропорта, периода, времени вылета и порога применяются; фильтр «Авиакомпании» здесь не учитывается.</Text>
        </Group>
      </Paper>

      {a && b && a === b && <EmptyNote>Выберите две разные авиакомпании.</EmptyNote>}
      {(!a || !b) && <EmptyNote>Выберите две авиакомпании для сравнения.</EmptyNote>}
      {error && <ErrorNote error={error} />}

      {data && a !== b && (
        <>
          <Paper p="md">
            <Table.ScrollContainer minWidth={520}>
              <Table withRowBorders striped>
                <Table.Thead>
                  <Table.Tr><Table.Th>Показатель</Table.Th><Table.Th ta="right">{data.a.name}</Table.Th><Table.Th ta="right">{data.b.name}</Table.Th></Table.Tr>
                </Table.Thead>
                <Table.Tbody className="num">
                  <Table.Tr><Table.Td>Выполнено рейсов</Table.Td><Table.Td ta="right">{fmtInt(data.a.kpi.flights)}</Table.Td><Table.Td ta="right">{fmtInt(data.b.kpi.flights)}</Table.Td></Table.Tr>
                  <Table.Tr><Table.Td>Доля задержанных</Table.Td><Table.Td ta="right"><b>{fmtPct(data.a.kpi.share)}</b></Table.Td><Table.Td ta="right"><b>{fmtPct(data.b.kpi.share)}</b></Table.Td></Table.Tr>
                  <Table.Tr><Table.Td>95% доверительный интервал</Table.Td><Table.Td ta="right">{fmtPct(data.a.kpi.ci_low)} – {fmtPct(data.a.kpi.ci_high)}</Table.Td><Table.Td ta="right">{fmtPct(data.b.kpi.ci_low)} – {fmtPct(data.b.kpi.ci_high)}</Table.Td></Table.Tr>
                  <Table.Tr><Table.Td>Средняя задержка</Table.Td><Table.Td ta="right">{fmtMin(data.a.kpi.avg_delay)}</Table.Td><Table.Td ta="right">{fmtMin(data.b.kpi.avg_delay)}</Table.Td></Table.Tr>
                  <Table.Tr><Table.Td>Максимальная задержка</Table.Td><Table.Td ta="right">{fmtInt(data.a.kpi.max_delay)} мин</Table.Td><Table.Td ta="right">{fmtInt(data.b.kpi.max_delay)} мин</Table.Td></Table.Tr>
                  <Table.Tr><Table.Td>Самый проблемный час вылета</Table.Td><Table.Td ta="right">{worstHour(data.a.kpi)}</Table.Td><Table.Td ta="right">{worstHour(data.b.kpi)}</Table.Td></Table.Tr>
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Paper>

          {data.diff ? (
            <Alert color="amber.5" variant="light" title="Различие в доле задержанных рейсов" styles={{ title: { color: '#0E2238', fontWeight: 600 } }}>
              <Text size="sm">
                <b>{data.a.name}</b> задерживает рейсы на <b>{fmtSigned(Math.abs(data.diff.diff) * 100, 1)} п.п.</b>{' '}
                {data.diff.diff >= 0 ? 'чаще' : 'реже'}, чем <b>{data.b.name}</b> (95% ДИ разности: {fmtSigned(data.diff.ci_low * 100, 1)} … {fmtSigned(data.diff.ci_high * 100, 1)} п.п.
                {data.diff.risk_ratio != null && <>; относительный риск ×{fmtNum(data.diff.risk_ratio, 2)}</>}). Критерий z: p {fmtP(data.diff.p_value)}.
              </Text>
              <Text size="xs" c="dimmed" mt={4}>При миллионах рейсов p-value почти всегда мало, поэтому судите по величине разницы и её доверительному интервалу.</Text>
            </Alert>
          ) : <EmptyNote>У одной из компаний нет рейсов при выбранных фильтрах.</EmptyNote>}

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            <ChartPanel title="Доля задержанных по часам вылета" option={hourlyOpt} loading={isFetching} height={320} />
            <ChartPanel title="Категории задержки прибытия" option={catOpt} loading={isFetching} height={320} />
          </SimpleGrid>
        </>
      )}
    </Stack>
  );
}
