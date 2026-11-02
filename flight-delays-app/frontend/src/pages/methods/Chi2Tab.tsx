import { Paper, Stack } from '@mantine/core';
import { useMethodsSummary } from '../../api/hooks';
import type { StatTest } from '../../api/types';
import { ErrorNote, PageLoader, Section } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { fmtInt, fmtNum, fmtP } from '../../utils/format';
import { EffectBadge, Note } from './Basics';

export default function Chi2Tab() {
  const { data, error } = useMethodsSummary();
  if (error) return <ErrorNote error={error} />;
  if (!data) return <PageLoader />;
  const columns: Column<StatTest>[] = [
    { key: 'title', header: 'Сравнение', render: (t) => t.title },
    { key: 'chi', header: 'χ²', align: 'right', render: (t) => fmtNum(t.statistic, 1), sortValue: (t) => t.statistic },
    { key: 'dof', header: 'Степени свободы', align: 'right', render: (t) => t.dof },
    { key: 'p', header: 'p-value', align: 'right', render: (t) => fmtP(t.p_value) },
    { key: 'n', header: 'Рейсов', align: 'right', render: (t) => fmtInt(t.n) },
    { key: 'v', header: 'V Крамера', align: 'right', render: (t) => <b>{fmtNum(t.effect_value, 3)}</b>, sortValue: (t) => t.effect_value },
    { key: 'label', header: 'Сила связи', render: (t) => <EffectBadge label={t.effect_label} /> },
  ];
  return (
    <Stack gap="md">
      <Section
        title="Хи-квадрат: различается ли доля задержанных рейсов"
        hint="Критерий проверяет независимость: одинакова ли доля задержанных рейсов у разных авиакомпаний и в разные периоды суток. Расчёт выполнен по всем рейсам."
      >
        <Paper p="md"><SortableTable rows={data.chi2} columns={columns} rowKey={(t) => t.code} minWidth={820} emptyText="Результаты ещё не рассчитаны" /></Paper>
      </Section>
      <Note>
        При миллионах рейсов значимым оказывается почти любое различие (p &lt; 0,001), поэтому главное — размер эффекта. V Крамера: до 0,1 — незначительная связь, 0,1–0,3 — слабая, 0,3–0,5 — умеренная, от 0,5 — сильная.
      </Note>
    </Stack>
  );
}
