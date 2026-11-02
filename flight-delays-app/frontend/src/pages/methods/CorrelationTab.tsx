import { Paper, Stack } from '@mantine/core';
import { useMemo } from 'react';
import { useMethodsSummary } from '../../api/hooks';
import type { StatTest } from '../../api/types';
import { forestOption } from '../../charts/options';
import { ChartPanel, ErrorNote, PageLoader, Section } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { fmtInt, fmtNum, fmtP } from '../../utils/format';
import { EffectBadge, Note } from './Basics';

export default function CorrelationTab() {
  const { data, error } = useMethodsSummary();
  const rows = data?.spearman ?? [];
  const option = useMemo(
    () => forestOption(rows.map((t) => ({ label: t.title, est: t.effect_value ?? 0, lo: t.effect_ci_low, hi: t.effect_ci_high })), { ref: 0, xName: 'Коэффициент Спирмена ρ (с 95% доверительным интервалом)', digits: 3 }),
    [rows],
  );
  if (error) return <ErrorNote error={error} />;
  if (!data) return <PageLoader />;

  const columns: Column<StatTest>[] = [
    { key: 'title', header: 'Пара признаков', render: (t) => t.title },
    { key: 'rho', header: 'ρ Спирмена', align: 'right', render: (t) => <b>{fmtNum(t.effect_value, 3)}</b>, sortValue: (t) => t.effect_value },
    { key: 'ci', header: '95% ДИ', align: 'right', render: (t) => `${fmtNum(t.effect_ci_low, 3)} … ${fmtNum(t.effect_ci_high, 3)}` },
    { key: 'p', header: 'p-value', align: 'right', render: (t) => fmtP(t.p_value) },
    { key: 'n', header: 'Рейсов в расчёте', align: 'right', render: (t) => fmtInt(t.n) },
    { key: 'label', header: 'Сила связи', render: (t) => <EffectBadge label={t.effect_label} /> },
  ];

  return (
    <Stack gap="md">
      <Section
        title="Корреляционный анализ: первый взгляд на связи"
        hint="Спирмен работает с рангами, поэтому устойчив к выбросам: у большинства рейсов задержки нет вовсе, а максимальная измеряется тысячами минут. Метод показывает силу и направление монотонной связи, но не отделяет влияние времени вылета от других факторов и не видит сезонность."
      >
        <Paper p="md"><SortableTable rows={rows} columns={columns} rowKey={(t) => t.code} minWidth={720} emptyText="Результаты ещё не рассчитаны" /></Paper>
      </Section>
      {rows.length > 0 && <ChartPanel title="Сила связи с задержкой" hint="Чем дальше точка от красной линии (ноль), тем сильнее связь. Сила связи: до 0,1 — практически нет, 0,1–0,3 — слабая, 0,3–0,5 — умеренная." option={option} height={Math.max(220, rows.length * 56 + 80)} />}
      <Note>Расчёт выполнен на случайной выборке рейсов. Положительное значение означает: чем позже вылет (больше значение признака), тем больше задержка.</Note>
    </Stack>
  );
}
