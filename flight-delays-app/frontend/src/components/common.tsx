import { Alert, Center, Group, Loader, Paper, Stack, Text, Title } from '@mantine/core';
import { IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';
import type { EChartsCoreOption } from 'echarts/core';
import type { ReactNode } from 'react';
import { ApiError } from '../api/client';
import { Chart } from './Chart';

export function PageLoader() {
  return (
    <Center py={80}>
      <Loader color="amber.5" />
    </Center>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg = error instanceof ApiError || error instanceof Error ? error.message : 'Не удалось загрузить данные';
  return (
    <Alert color="red" icon={<IconAlertCircle size={18} />} title="Ошибка загрузки">
      {msg}
    </Alert>
  );
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return (
    <Alert color="gray" variant="light" icon={<IconInfoCircle size={18} />}>
      {children}
    </Alert>
  );
}

export function Section({ title, hint, right, children }: { title: string; hint?: ReactNode; right?: ReactNode; children: ReactNode }) {
  return (
    <Stack gap="xs">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <div>
          <Title order={3} size="h4" className="page-title">{title}</Title>
          {hint && <Text size="sm" c="dimmed" maw={760}>{hint}</Text>}
        </div>
        {right}
      </Group>
      {children}
    </Stack>
  );
}

export function ChartPanel({ title, hint, option, height = 320, loading = false }: {
  title: string; hint?: ReactNode; option: EChartsCoreOption | null; height?: number; loading?: boolean;
}) {
  return (
    <Paper p="md">
      <Title order={4} size="h5" className="page-title">{title}</Title>
      {hint && <Text size="sm" c="dimmed" mb={4}>{hint}</Text>}
      <Chart option={option} height={height} loading={loading} />
    </Paper>
  );
}
