import { Container, Stack, Tabs, Text, Title } from '@mantine/core';
import { useSearchParams } from 'react-router-dom';
import { useMethodsSummary } from '../api/hooks';
import { Board } from './methods/Basics';
import Chi2Tab from './methods/Chi2Tab';
import CorrelationTab from './methods/CorrelationTab';
import KruskalTab from './methods/KruskalTab';
import LimitsTab from './methods/LimitsTab';
import RegressionTab from './methods/RegressionTab';
import { fmtInt, fmtPct } from '../utils/format';

const TABS = ['correlation', 'chi2', 'kruskal', 'regression', 'limits'];

export default function Methods() {
  const [sp, setSp] = useSearchParams();
  const { data } = useMethodsSummary();
  const requested = sp.get('tab') ?? 'regression';
  const tab = TABS.includes(requested) ? requested : 'regression';
  const sample = data?.sample;

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <div>
          <Title order={2} className="page-title">Методы анализа и результаты</Title>
          <Text size="sm" c="dimmed" maw={860}>
            Четыре шага, каждый из которых отвечает на вопрос, оставшийся после предыдущего: корреляция показывает, есть ли связь; критерии — одинаковы ли группы; регрессия — насколько сильно и при прочих равных условиях. Описательные агрегаты — это панель показателей.
          </Text>
        </div>
        {sample && (
          <Board items={[
            { label: 'Рейсов в выборке для статистик', value: fmtInt(sample.rows), amber: true, sub: sample.fraction != null ? `доля от всех рейсов ≈ ${fmtPct(sample.fraction, 0)}` : undefined },
            { label: 'Обучение / проверка моделей', value: sample.train_rows ? `${fmtInt(sample.train_rows)} / ${fmtInt(sample.test_rows)}` : '—', sub: 'случайное разбиение 2 : 1' },
          ]} />
        )}
        <Tabs value={tab} keepMounted={false} color="amber.5" onChange={(v) => setSp((prev) => { const n = new URLSearchParams(prev); n.set('tab', v ?? 'regression'); return n; }, { replace: true })}>
          <Tabs.List style={{ flexWrap: 'nowrap', overflowX: 'auto' }}>
            <Tabs.Tab value="correlation">1. Корреляции</Tabs.Tab>
            <Tabs.Tab value="chi2">2. Хи-квадрат</Tabs.Tab>
            <Tabs.Tab value="kruskal">3. Краскел — Уоллис и Данн</Tabs.Tab>
            <Tabs.Tab value="regression">4. Регрессия</Tabs.Tab>
            <Tabs.Tab value="limits">Ограничения</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="correlation" pt="md"><CorrelationTab /></Tabs.Panel>
          <Tabs.Panel value="chi2" pt="md"><Chi2Tab /></Tabs.Panel>
          <Tabs.Panel value="kruskal" pt="md"><KruskalTab /></Tabs.Panel>
          <Tabs.Panel value="regression" pt="md"><RegressionTab /></Tabs.Panel>
          <Tabs.Panel value="limits" pt="md"><LimitsTab /></Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
