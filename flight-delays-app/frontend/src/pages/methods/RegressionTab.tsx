import { Accordion, Alert, Group, Input, Paper, SegmentedControl, SimpleGrid, Stack, TextInput } from '@mantine/core';
import { useMemo, useState } from 'react';
import { useRegression } from '../../api/hooks';
import type { Coef } from '../../api/types';
import { barsHeight, calibrationOption, forestOption, hourProbabilityOption } from '../../charts/options';
import { ChartPanel, EmptyNote, ErrorNote, PageLoader, Section } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { fmtInt, fmtNum, fmtP, fmtPct, fmtSigned } from '../../utils/format';
import { Board, Note } from './Basics';

interface EffectRow { key: string; model: string; effect: string; est: string; ci: string; p: string }
interface JoinedRow { term: string; label: string; lin?: Coef; logit?: Coef }

const ci = (lo: number | null, hi: number | null, f: (x: number | null) => string) => `${f(lo)} … ${f(hi)}`;
const minutes = (x: number | null) => fmtSigned(x, 2);
const ratio = (x: number | null) => fmtNum(x, 2);

function join(linear: Coef[], logit: Coef[], groups: string[]): JoinedRow[] {
  const lin = new Map(linear.filter((c) => groups.includes(c.grp)).map((c) => [c.term, c]));
  return logit.filter((c) => groups.includes(c.grp)).map((c) => ({ term: c.term, label: c.label, lin: lin.get(c.term), logit: c }));
}

export default function RegressionTab() {
  const { data, error } = useRegression();
  const [kind, setKind] = useState<'logit' | 'linear'>('logit');
  const [search, setSearch] = useState('');
  const models = useMemo(() => Object.fromEntries((data?.models ?? []).map((m) => [m.code, m])), [data]);
  const logit = models['logit_period'];
  const linHour = models['linear_hour'];
  const linPeriod = models['linear_period'];
  const logit15 = models['logit_period_15'];

  const airlineOption = useMemo(() => {
    const m = kind === 'logit' ? logit : linHour;
    const rows = (m?.coefficients ?? []).filter((c) => c.grp === 'airline').map((c) => (kind === 'logit'
      ? { label: c.label, est: c.odds_ratio ?? 1, lo: c.or_ci_low, hi: c.or_ci_high }
      : { label: c.label, est: c.estimate, lo: c.ci_low, hi: c.ci_high })).sort((a, b) => b.est - a.est);
    return {
      count: rows.length,
      option: forestOption(rows, kind === 'logit'
        ? { ref: 1, log: true, xName: 'Отношение шансов задержки относительно «средней» авиакомпании' }
        : { ref: 0, xName: 'Минуты задержки относительно «средней» авиакомпании' }),
    };
  }, [kind, logit, linHour]);

  const stabilityOption = useMemo(() => forestOption(
    (data?.hour_stability ?? []).map((c) => ({ label: c.label, est: c.estimate, lo: c.ci_low, hi: c.ci_high })),
    { ref: 0, xName: 'Минут задержки на каждый час более позднего вылета' }), [data]);
  const probabilityOption = useMemo(() => (data?.hour_probability ? hourProbabilityOption(data.hour_probability) : null), [data]);
  const calibration = useMemo(() => (data?.calibration?.length ? calibrationOption(data.calibration) : null), [data]);

  if (error) return <ErrorNote error={error} />;
  if (!data) return <PageLoader />;
  if (!logit || !linHour) return <EmptyNote>Регрессионные модели ещё не рассчитаны: выборка слишком мала или конвейер не запускался.</EmptyNote>;

  // ── Эффект времени вылета ──
  const timeRows: EffectRow[] = [
    ...linHour.coefficients.filter((c) => c.grp === 'time').map((c) => ({ key: `lh-${c.term}`, model: 'Линейная: минуты задержки', effect: c.label, est: `${minutes(c.estimate)} мин`, ci: ci(c.ci_low, c.ci_high, minutes), p: fmtP(c.p_value) })),
    ...(linPeriod?.coefficients ?? []).filter((c) => c.grp === 'time').map((c) => ({ key: `lp-${c.term}`, model: 'Линейная: минуты задержки', effect: c.label, est: `${minutes(c.estimate)} мин`, ci: ci(c.ci_low, c.ci_high, minutes), p: fmtP(c.p_value) })),
    ...logit.coefficients.filter((c) => c.grp === 'time').map((c) => ({ key: `gp-${c.term}`, model: 'Логистическая: шансы задержки > 0 мин', effect: c.label, est: `×${ratio(c.odds_ratio)}`, ci: ci(c.or_ci_low, c.or_ci_high, ratio), p: fmtP(c.p_value) })),
    ...(logit15?.coefficients ?? []).filter((c) => c.grp === 'time').map((c) => ({ key: `g15-${c.term}`, model: 'Логистическая: шансы задержки ≥ 15 мин', effect: c.label, est: `×${ratio(c.odds_ratio)}`, ci: ci(c.or_ci_low, c.or_ci_high, ratio), p: fmtP(c.p_value) })),
  ];
  const timeColumns: Column<EffectRow>[] = [
    { key: 'model', header: 'Модель', render: (r) => r.model },
    { key: 'effect', header: 'Эффект', render: (r) => r.effect },
    { key: 'est', header: 'Оценка', align: 'right', render: (r) => <b>{r.est}</b> },
    { key: 'ci', header: '95% ДИ', align: 'right', render: (r) => r.ci },
    { key: 'p', header: 'p-value', align: 'right', render: (r) => r.p },
  ];

  // ── Календарь, длительность, аэропорты ──
  const calendar = join(linHour.coefficients, logit.coefficients, ['calendar', 'duration']);
  const airports = join(linHour.coefficients, logit.coefficients, ['airport'])
    .filter((r) => r.label.toLowerCase().includes(search.trim().toLowerCase()));
  const joinedColumns = (title: string): Column<JoinedRow>[] => [
    { key: 'label', header: title, render: (r) => r.label, sortValue: (r) => r.label },
    { key: 'min', header: 'Минуты (линейная)', align: 'right', render: (r) => (r.lin ? `${minutes(r.lin.estimate)}` : '—'), sortValue: (r) => r.lin?.estimate },
    { key: 'minci', header: '95% ДИ', align: 'right', render: (r) => (r.lin ? ci(r.lin.ci_low, r.lin.ci_high, minutes) : '—') },
    { key: 'or', header: 'Шансы (логистическая)', align: 'right', render: (r) => (r.logit?.odds_ratio != null ? `×${ratio(r.logit.odds_ratio)}` : '—'), sortValue: (r) => r.logit?.odds_ratio },
    { key: 'orci', header: '95% ДИ', align: 'right', render: (r) => (r.logit ? ci(r.logit.or_ci_low, r.logit.or_ci_high, ratio) : '—') },
  ];

  const m = logit.metrics;
  const lm = linHour.metrics;
  return (
    <Stack gap="lg">
      <Board items={[
        { label: 'AUC на проверочной выборке', value: fmtNum(m.auc_test, 3), amber: true, sub: '0,5 — как случайное угадывание, 1 — идеал' },
        { label: 'Доля разброса минут, объяснённая моделью (R²)', value: fmtPct(lm.r2_test, 1), sub: 'линейная модель, проверочная выборка' },
        { label: 'Доля задержанных в выборке', value: fmtPct(m.base_rate, 1), sub: 'базовый уровень для логистической модели' },
        { label: 'Рейсов: обучение / проверка', value: `${fmtInt(m.n_train)} / ${fmtInt(m.n_test)}`, sub: 'модель оценена на невиденных данных' },
      ]} />

      <Section
        title="Время вылета при прочих равных"
        hint="Модели одновременно учитывают авиакомпанию, аэропорт, длительность, день недели, месяц и год. Если коэффициент при часе вылета почти не меняется от добавления контролей, рост задержек к вечеру не объясняется составом рейсов."
      >
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
          <ChartPanel title="Устойчивость эффекта часа вылета" hint="Контроли добавляются по одному; точка — оценка, «усы» — 95% ДИ." option={stabilityOption} height={300} />
          {probabilityOption && <ChartPanel title="Вероятность задержки по часам" hint="Пунктир — наблюдаемая доля; сплошная — модель при одинаковом составе рейсов (авиакомпании, аэропорты, календарь). Разница между линиями и есть поправка на состав рейсов." option={probabilityOption} height={300} />}
        </SimpleGrid>
        <Paper p="md"><SortableTable rows={timeRows} columns={timeColumns} rowKey={(r) => r.key} minWidth={760} /></Paper>
        <Note>Периоды суток сравниваются с утром (06–11 ч). Шансы ×2,0 означают: шансы задержки вдвое выше. Шансы — не вероятность: вероятность см. на графике справа.</Note>
      </Section>

      <Section
        title="Авиакомпании при прочих равных"
        hint="Сравнение со «средней» авиакомпанией (невзвешенное среднее по компаниям) после учёта времени вылета, аэропорта, длительности и календаря."
        right={<Input.Wrapper label="Показатель"><SegmentedControl size="xs" value={kind} onChange={(v) => setKind(v as 'logit' | 'linear')} data={[{ value: 'logit', label: 'Шансы задержки' }, { value: 'linear', label: 'Минуты задержки' }]} /></Input.Wrapper>}
      >
        <ChartPanel title={kind === 'logit' ? 'Отношение шансов по авиакомпаниям' : 'Эффект авиакомпании в минутах'} hint={kind === 'logit' ? 'Правее красной линии (1) — шансы задержки выше среднего.' : 'Правее красной линии (0) — задержки длиннее средних.'} option={airlineOption.option} height={barsHeight(airlineOption.count, 30)} />
      </Section>

      <Section title="Длительность перелёта и календарь" hint="Сезонность корреляция не замечает, регрессия — видит. Оценки по месяцам осторожные, если данные за часть месяцев есть только за один год.">
        <Paper p="md"><SortableTable rows={calendar} columns={joinedColumns('Фактор')} rowKey={(r) => r.term} minWidth={760} /></Paper>
      </Section>

      <Accordion variant="contained">
        <Accordion.Item value="airports">
          <Accordion.Control>Аэропорты вылета: эффект при прочих равных</Accordion.Control>
          <Accordion.Panel>
            <Stack gap="sm">
              <Group><TextInput placeholder="Поиск по коду аэропорта" value={search} onChange={(e) => setSearch(e.currentTarget.value)} w={280} aria-label="Поиск аэропорта" /></Group>
              <SortableTable rows={airports} columns={joinedColumns('Аэропорт')} rowKey={(r) => r.term} minWidth={760} initialSort={{ key: 'or', dir: 'desc' }} />
              <Note>Малые аэропорты объединены в группу «Прочие аэропорты», чтобы оценки не опирались на единичные рейсы. Сравнение — со «средним» аэропортом.</Note>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      {calibration && (
        <Section title="Калибровка модели" hint="Рейсы разбиты на 10 групп по предсказанной вероятности. Точки вдоль диагонали означают, что предсказанные вероятности близки к фактическим долям.">
          <ChartPanel title="Предсказанная и фактическая доля задержек" option={calibration} height={340} />
        </Section>
      )}
      {m.auc_test != null && m.auc_test < 0.6 && <Alert color="yellow">AUC ниже 0,6: модель слабо различает задержанные и вовремя прибывшие рейсы.</Alert>}
    </Stack>
  );
}
