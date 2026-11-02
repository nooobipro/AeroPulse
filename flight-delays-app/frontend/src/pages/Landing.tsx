import { Alert, Box, Button, Container, Divider, Group, List, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { useHighlights, useMe } from '../api/hooks';
import type { Highlights } from '../api/types';
import { PageLoader } from '../components/common';
import { fmtHour, fmtInt, fmtPct, fmtPeriod } from '../utils/format';

/** «Табло» с долей задержанных рейсов по часам вылета — главный результат проекта в одном взгляде. */
export function DepartureBoard({ hourly }: { hourly: Highlights['hourly'] }) {
  const rows = hourly.filter((h) => h.hour >= 6 && h.hour <= 22 && h.hour % 2 === 0);
  const shown = rows.length >= 4 ? rows : hourly.slice(0, 9);
  const max = Math.max(...shown.map((r) => r.share), 0.01);
  return (
    <div className="board" style={{ padding: '14px 20px 8px' }} role="img" aria-label="Табло: доля задержанных рейсов по часам вылета">
      <div className="board-label" style={{ paddingBottom: 8 }}>Доля задержанных рейсов по часам вылета</div>
      {shown.map((r) => (
        <div className="dep-row" key={r.hour}>
          <span className="dep-hour">{fmtHour(r.hour)}</span>
          <span className="dep-bar"><span style={{ width: `${(r.share / max) * 100}%` }} /></span>
          <span className="dep-share">{fmtPct(r.share, 0)}</span>
        </div>
      ))}
    </div>
  );
}

function Findings({ hl }: { hl: Highlights }) {
  const morning = hl.periods.find((p) => p.code === 'morning');
  const evening = hl.periods.find((p) => p.code === 'evening');
  return (
    <Stack gap="md">
      {morning?.share != null && evening?.share != null && (
        <Text>Утром ({fmtHour(morning.hour_from)}–{fmtHour(morning.hour_to)}) с опозданием прибывает <b>{fmtPct(morning.share, 0)}</b> рейсов, вечером ({fmtHour(evening.hour_from)}–{fmtHour(evening.hour_to)}) — <b>{fmtPct(evening.share, 0)}</b>.</Text>
      )}
      <Divider />
      {hl.best_airline && hl.worst_airline && (
        <Text>Пунктуальность авиакомпаний различается: доля задержанных рейсов — от <b>{fmtPct(hl.best_airline.share, 0)}</b> ({hl.best_airline.name}) до <b>{fmtPct(hl.worst_airline.share, 0)}</b> ({hl.worst_airline.name}).</Text>
      )}
      <Divider />
      <Text>
        Проанализировано <b>{fmtInt(hl.flights)}</b> выполненных рейсов: {hl.airlines} авиакомпаний, {hl.airports} аэропортов вылета.
        {hl.share15 != null && <> С опозданием на 15 минут и более прибывает {fmtPct(hl.share15, 0)} рейсов.</>}
      </Text>
      <Divider />
      <Text c="dimmed" size="sm">Связь времени вылета с задержкой измерена статистически, но причин задержек (погода, загрузка аэропортов, опоздание предыдущего рейса) в данных нет — поэтому мы говорим «связано с», а не «вызывает».</Text>
    </Stack>
  );
}

const ROLES: { title: string; items: string[] }[] = [
  { title: 'Пользователь', items: ['Показатели пунктуальности с фильтрами по авиакомпании, аэропорту, периоду и времени вылета', 'Рейтинг авиакомпаний с доверительными интервалами', 'Анализ по часам, дням недели и аэропортам', 'Сравнение двух авиакомпаний'] },
  { title: 'Аналитик', items: ['Всё, что доступно пользователю', 'Результаты корреляционного, хи-квадрат, непараметрического и регрессионного анализа', 'Отчёты в Excel и PDF, выгрузка таблиц в CSV', 'Сохранённые наборы фильтров'] },
  { title: 'Администратор', items: ['Управление пользователями и ролями', 'Журнал действий', 'Справочники авиакомпаний и аэропортов', 'Сведения о загруженных данных'] },
];

export default function Landing() {
  const { data: hl, isLoading } = useHighlights();
  const { data: me } = useMe();

  return (
    <>
      <Box style={{ borderBottom: '1px solid var(--line)' }} bg="white">
        <Container size="xl" py={{ base: 28, md: 56 }}>
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing={48}>
            <Stack gap="md" justify="center">
              <Title order={1} className="page-title" fz={{ base: 34, md: 48 }} lh={1.05}>
                Насколько пунктуальны рейсы и от чего это зависит
              </Title>
              <Text size="lg" maw={560} c="dimmed">
                Анализ задержек прибытия: как они зависят от времени вылета и чем различаются авиакомпании. Интерактивные показатели, графики и результаты статистического анализа.
              </Text>
              <Group mt="xs">
                {me ? (
                  <Button component={Link} to="/dashboard" size="md" color="amber.5" c="#0E2238">Открыть панель</Button>
                ) : (
                  <>
                    <Button component={Link} to="/register" size="md" color="amber.5" c="#0E2238">Создать аккаунт</Button>
                    <Button component={Link} to="/login" size="md" variant="default">Войти</Button>
                  </>
                )}
              </Group>
              {!me && <Text size="sm" c="dimmed">Подробные показатели доступны после входа.</Text>}
            </Stack>
            <div>{isLoading ? <PageLoader /> : hl?.has_data ? <DepartureBoard hourly={hl.hourly} /> : null}</div>
          </SimpleGrid>
        </Container>
      </Box>

      <Container size="xl" py={48}>
        {isLoading ? null : !hl?.has_data ? (
          <Alert icon={<IconInfoCircle size={18} />} color="gray" title="Данные ещё не загружены">
            Администратору нужно выполнить загрузку данных конвейером (см. README, раздел «Загрузка данных»).
          </Alert>
        ) : (
          <SimpleGrid cols={{ base: 1, md: 3 }} spacing={48}>
            <div>
              <Title order={2} className="page-title">Что показывают данные</Title>
              {hl.period_start && hl.period_end && <Text c="dimmed" mt={4}>{fmtPeriod(hl.period_start)} — {fmtPeriod(hl.period_end)}</Text>}
            </div>
            <Box style={{ gridColumn: 'span 2' }}><Findings hl={hl} /></Box>
          </SimpleGrid>
        )}

        <Divider my={48} />
        <Title order={2} className="page-title" mb="lg">Что доступно по ролям</Title>
        <SimpleGrid cols={{ base: 1, md: 3 }} spacing={32}>
          {ROLES.map((r) => (
            <div key={r.title}>
              <Title order={3} size="h4" className="page-title" mb="xs">{r.title}</Title>
              <List size="sm" spacing={6}>{r.items.map((i) => <List.Item key={i}>{i}</List.Item>)}</List>
            </div>
          ))}
        </SimpleGrid>
      </Container>
    </>
  );
}
