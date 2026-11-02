import { Badge, Group, Paper, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { useDataInfo } from '../../api/hooks';
import { ErrorNote, PageLoader } from '../../components/common';
import { Board } from '../methods/Basics';
import { fmtDateTime, fmtInt, fmtPeriod } from '../../utils/format';

const NOTE_LABELS: Record<string, string> = {
  rows_total: 'Строк в исходных файлах',
  completed: 'Выполненных рейсов (использовано в анализе)',
  cancelled: 'Отменённых рейсов',
  diverted: 'Перенаправленных рейсов',
  rows_invalid: 'Отброшено: нет даты, времени, авиакомпании или аэропорта',
  rows_missing_delay: 'Выполнены, но задержка прибытия не указана',
};
const COUNT_LABELS: Record<string, string> = {
  users: 'Пользователей', aggregate_rows: 'Строк агрегатов', airlines: 'Авиакомпаний в справочнике',
  airports: 'Аэропортов в справочнике', stat_tests: 'Статистических критериев', audit_records: 'Записей журнала',
};

export default function DataTab() {
  const { data, error } = useDataInfo();
  if (error) return <ErrorNote error={error} />;
  if (!data) return <PageLoader />;
  const v = data.current;
  if (!v) return <Text>Данные ещё не загружены. Запустите конвейер загрузки (см. README).</Text>;

  return (
    <Stack gap="md">
      <Board items={[
        { label: 'Период данных', value: `${v.period_start} — ${v.period_end}`, sub: `${fmtPeriod(v.period_start)} — ${fmtPeriod(v.period_end)}`, amber: true },
        { label: 'Рейсов в анализе', value: fmtInt(v.rows_used), sub: `из ${fmtInt(v.rows_total)} строк` },
        { label: 'Авиакомпаний / аэропортов', value: `${v.airlines} / ${v.airports}` },
        { label: 'Загружено', value: fmtDateTime(v.loaded_at) },
      ]} />
      <Paper p="md">
        <Group gap="xs" mb="xs">
          <Title order={4} size="h5" className="page-title">Источник</Title>
          {v.is_demo && <Badge color="yellow">демонстрационные данные</Badge>}
        </Group>
        <Text size="sm">{v.source || '—'}</Text>
      </Paper>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Paper p="md">
          <Title order={4} size="h5" className="page-title" mb="xs">Обработка исходных строк</Title>
          <Table withRowBorders>
            <Table.Tbody>
              {Object.entries(NOTE_LABELS).map(([k, label]) => v.notes && k in v.notes && (
                <Table.Tr key={k}><Table.Td>{label}</Table.Td><Table.Td ta="right" className="num">{fmtInt(v.notes[k] as number)}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
        <Paper p="md">
          <Title order={4} size="h5" className="page-title" mb="xs">Содержимое базы</Title>
          <Table withRowBorders>
            <Table.Tbody>
              {Object.entries(data.counts).map(([k, n]) => (
                <Table.Tr key={k}><Table.Td>{COUNT_LABELS[k] ?? k}</Table.Td><Table.Td ta="right" className="num">{fmtInt(n)}</Table.Td></Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      </SimpleGrid>
      <Paper p="md">
        <Title order={4} size="h5" className="page-title" mb="xs">История загрузок</Title>
        <Table.ScrollContainer minWidth={560}>
          <Table withRowBorders striped>
            <Table.Thead><Table.Tr><Table.Th>Загружено</Table.Th><Table.Th>Период</Table.Th><Table.Th ta="right">Рейсов</Table.Th><Table.Th>Тип</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {data.history.map((h) => (
                <Table.Tr key={h.id}>
                  <Table.Td>{fmtDateTime(h.loaded_at)}</Table.Td><Table.Td>{h.period_start} — {h.period_end}</Table.Td>
                  <Table.Td ta="right" className="num">{fmtInt(h.rows_used)}</Table.Td><Table.Td>{h.is_demo ? 'демо' : 'реальные данные'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>
    </Stack>
  );
}

