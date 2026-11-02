import { Badge, Group, Input, Pagination, Paper, Select, Stack, Switch } from '@mantine/core';
import { useMemo, useState } from 'react';
import { useDunn, useMethodsSummary } from '../../api/hooks';
import type { DunnRow, StatTest } from '../../api/types';
import { ErrorNote, PageLoader, Section } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { fmtInt, fmtNum, fmtP } from '../../utils/format';
import { EffectBadge, Note } from './Basics';

const PAGE = 20;

export default function KruskalTab() {
  const summary = useMethodsSummary();
  const dunn = useDunn();
  const [onlySig, setOnlySig] = useState(false);
  const [airline, setAirline] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const airlines = useMemo(() => {
    const names = new Set<string>();
    (dunn.data ?? []).forEach((r) => { names.add(r.airline_a); names.add(r.airline_b); });
    return [...names].sort((a, b) => a.localeCompare(b, 'ru'));
  }, [dunn.data]);

  const filtered = useMemo(
    () => (dunn.data ?? []).filter((r) => (!onlySig || r.significant) && (!airline || r.airline_a === airline || r.airline_b === airline)),
    [dunn.data, onlySig, airline],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const shown = filtered.slice((Math.min(page, pages) - 1) * PAGE, Math.min(page, pages) * PAGE);

  if (summary.error || dunn.error) return <ErrorNote error={summary.error ?? dunn.error} />;
  if (!summary.data || !dunn.data) return <PageLoader />;

  const kwColumns: Column<StatTest>[] = [
    { key: 'title', header: 'Сравнение', render: (t) => t.title },
    { key: 'h', header: 'H', align: 'right', render: (t) => fmtNum(t.statistic, 1) },
    { key: 'dof', header: 'Степени свободы', align: 'right', render: (t) => t.dof },
    { key: 'p', header: 'p-value', align: 'right', render: (t) => fmtP(t.p_value) },
    { key: 'n', header: 'Рейсов', align: 'right', render: (t) => fmtInt(t.n) },
    { key: 'e', header: 'ε²', align: 'right', render: (t) => <b>{fmtNum(t.effect_value, 3)}</b> },
    { key: 'label', header: 'Размер эффекта', render: (t) => <EffectBadge label={t.effect_label} /> },
  ];
  const dunnColumns: Column<DunnRow>[] = [
    { key: 'pair', header: 'Пара авиакомпаний', render: (r) => `${r.airline_a} — ${r.airline_b}`, sortValue: (r) => `${r.airline_a} ${r.airline_b}` },
    { key: 'z', header: 'z', align: 'right', render: (r) => fmtNum(r.z, 2), sortValue: (r) => r.z },
    { key: 'p', header: 'p с поправкой', align: 'right', render: (r) => fmtP(r.p_adj), sortValue: (r) => r.p_adj },
    { key: 'dir', header: 'Где задержки больше', render: (r) => (!r.significant ? '—' : r.z > 0 ? r.airline_a : r.airline_b) },
    { key: 'sig', header: 'Вывод', render: (r) => <Badge variant="light" color={r.significant ? 'orange' : 'gray'} radius="sm">{r.significant ? 'различаются' : 'не различаются'}</Badge> },
  ];

  return (
    <Stack gap="md">
      <Section
        title="Краскел — Уоллис: насколько сильно опаздывают"
        hint="Задержки скошены (много нулей и редкие огромные значения), поэтому сравниваются ранги, а не средние. Критерий показывает, различаются ли группы по величине задержки в минутах."
      >
        <Paper p="md"><SortableTable rows={summary.data.kruskal} columns={kwColumns} rowKey={(t) => t.code} minWidth={820} emptyText="Результаты ещё не рассчитаны" /></Paper>
      </Section>
      <Note>
        ε² показывает, какую долю разброса рангов задержек объясняет группа: до 0,01 — незначительная, 0,01–0,06 — малая, 0,06–0,14 — средняя. Значимость при большой выборке почти гарантирована, поэтому смотрите на размер эффекта.
        Средние задержки, которые выводятся на панели, зависят от режима «по всем рейсам / только по задержанным» — это ответы на разные вопросы.
      </Note>

      <Section
        title="Парные сравнения Данна"
        hint={`Какие именно авиакомпании различаются. p-value скорректированы поправкой Бонферрони на число пар (${dunn.data.length}).`}
        right={
          <Group gap="md" align="flex-end">
            <Select label="Авиакомпания" placeholder="Все" data={airlines} value={airline} onChange={(v) => { setAirline(v); setPage(1); }} clearable searchable w={240} />
            <Input.Wrapper label="Только значимые"><Switch mt={6} checked={onlySig} onChange={(e) => { setOnlySig(e.currentTarget.checked); setPage(1); }} aria-label="Только значимые различия" /></Input.Wrapper>
          </Group>
        }
      >
        <Paper p="md">
          <SortableTable rows={shown} columns={dunnColumns} rowKey={(r) => `${r.airline_a_id}-${r.airline_b_id}`} initialSort={{ key: 'p', dir: 'asc' }} minWidth={760} emptyText="Нет пар, удовлетворяющих условиям" />
          {pages > 1 && <Group justify="center" mt="md"><Pagination total={pages} value={Math.min(page, pages)} onChange={setPage} size="sm" /></Group>}
        </Paper>
      </Section>
    </Stack>
  );
}
