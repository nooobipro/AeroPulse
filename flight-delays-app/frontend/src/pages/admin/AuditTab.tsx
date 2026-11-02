import { Group, Pagination, Paper, Select, Stack, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useState } from 'react';
import { useAudit } from '../../api/hooks';
import type { AuditRecord } from '../../api/types';
import { ErrorNote } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { ACTION_LABEL, fmtDateTime } from '../../utils/format';

const ACTIONS = Object.entries(ACTION_LABEL).map(([value, label]) => ({ value, label }));

export default function AuditTab() {
  const [action, setAction] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [debounced] = useDebouncedValue(email, 300);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const audit = useAudit({ action, email: debounced, dateFrom, dateTo, page });
  const pages = Math.max(1, Math.ceil((audit.data?.total ?? 0) / (audit.data?.page_size ?? 20)));
  const reset = <T,>(set: (v: T) => void) => (v: T) => { set(v); setPage(1); };

  const columns: Column<AuditRecord>[] = [
    { key: 'time', header: 'Время', render: (r) => fmtDateTime(r.created_at) },
    { key: 'user', header: 'Пользователь', render: (r) => r.user_email || '—' },
    { key: 'action', header: 'Действие', render: (r) => ACTION_LABEL[r.action] ?? r.action },
    { key: 'details', header: 'Подробности', render: (r) => <Text size="sm" style={{ wordBreak: 'break-word' }}>{r.details || '—'}</Text> },
    { key: 'ip', header: 'IP', render: (r) => r.ip || '—' },
  ];

  return (
    <Stack gap="md">
      <Paper p="md">
        <Group align="flex-end" gap="md" wrap="wrap">
          <Select label="Действие" placeholder="Все" data={ACTIONS} value={action} onChange={reset(setAction)} clearable searchable w={280} />
          <TextInput label="Email пользователя" placeholder="Часть адреса" value={email} onChange={(e) => reset(setEmail)(e.currentTarget.value)} w={240} />
          <TextInput label="С даты" type="date" value={dateFrom} onChange={(e) => reset(setDateFrom)(e.currentTarget.value)} />
          <TextInput label="По дату" type="date" value={dateTo} onChange={(e) => reset(setDateTo)(e.currentTarget.value)} />
          <Text size="sm" c="dimmed">Записей: {audit.data?.total ?? '…'}</Text>
        </Group>
      </Paper>
      {audit.error && <ErrorNote error={audit.error} />}
      <Paper p="md">
        <SortableTable rows={audit.data?.items ?? []} columns={columns} rowKey={(r) => r.id} minWidth={820} emptyText="Записей нет" />
        {pages > 1 && <Group justify="center" mt="md"><Pagination total={pages} value={page} onChange={setPage} size="sm" /></Group>}
      </Paper>
    </Stack>
  );
}
