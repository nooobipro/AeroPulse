import { List, Paper, Stack, Text } from '@mantine/core';
import { useFilterOptions, useMethodsSummary, useRegression } from '../../api/hooks';
import { Section } from '../../components/common';
import { fmtInt, fmtNum, fmtPct } from '../../utils/format';

export default function LimitsTab() {
  const { data: summary } = useMethodsSummary();
  const { data: reg } = useRegression();
  const { data: opts } = useFilterOptions();
  const logit = reg?.models.find((m) => m.code === 'logit_period');
  const linear = reg?.models.find((m) => m.code === 'linear_hour');
  const s = summary?.sample ?? reg?.sample ?? null;
  const months = opts?.periods.length;

  return (
    <Stack gap="md">
      <Section title="Границы выводов" hint="Что можно и нельзя утверждать по результатам анализа.">
        <Paper p="md">
          <List spacing="sm" size="sm">
            <List.Item>
              <b>Модель оценивает риск, а не предсказывает конкретный рейс.</b>{' '}
              {logit?.metrics.auc_test != null && <>AUC на проверочной выборке — {fmtNum(logit.metrics.auc_test, 3)}</>}
              {linear?.metrics.r2_test != null && <>, линейная модель объясняет {fmtPct(linear.metrics.r2_test, 1)} разброса минут задержки.</>}{' '}
              Зато предсказанные вероятности близки к фактическим долям (см. калибровку).
            </List.Item>
            <List.Item><b>Связь — не причина.</b> В данных нет причин задержек: погоды, загрузки аэропортов, задержки предыдущего рейса того же самолёта. Поэтому везде «связано с», а не «вызывает». Гипотеза каскадного накопления задержек согласуется с данными, но не доказана.</List.Item>
            <List.Item><b>Период наблюдения ограничен{months ? ` (${months} мес.)` : ''}.</b> Уровень задержек меняется со временем, а часть месяцев представлена только одним годом, поэтому сезонные оценки осторожные.</List.Item>
            <List.Item><b>Значимость — не важность.</b> При миллионах рейсов значимой оказывается почти любая связь. Выводы опираются на размер эффекта (ρ, V Крамера, ε², отношения шансов) и качество модели.</List.Item>
            {s && (
              <List.Item>
                <b>Статистики считались на случайной выборке</b> из {fmtInt(s.rows)} рейсов{s.train_rows ? <> (обучающая часть — {fmtInt(s.train_rows)}, проверочная — {fmtInt(s.test_rows)})</> : null}. Хи-квадрат, доли и средние на панели — по всем рейсам.
              </List.Item>
            )}
            <List.Item><b>Как измеряется задержка.</b> Это опоздание прибытия относительно расписания в минутах; досрочное прибытие равно нулю. Отменённые и перенаправленные рейсы исключены. «Задержан» — опоздание больше 0 минут; для проверки используется порог 15 минут и более.</List.Item>
            <List.Item><b>Время суток</b> определяется по местному времени аэропорта вылета: ночь 00–05, утро 06–11, день 12–17, вечер 18–23 ч.</List.Item>
          </List>
        </Paper>
      </Section>
      <Text size="sm" c="dimmed">Эти результаты рассчитывает офлайн-конвейер при загрузке данных; приложение их только отображает.</Text>
    </Stack>
  );
}
