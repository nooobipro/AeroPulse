import { ActionIcon, Button, Group, Modal, Pagination, Paper, Select, Stack, Switch, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconSearch, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { useAdminUsers, useDeleteUser, useMe, useUpdateUser } from '../../api/hooks';
import type { User } from '../../api/types';
import { ErrorNote } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';
import { ROLE_LABEL, fmtDateTime } from '../../utils/format';

const ROLE_OPTIONS = Object.entries(ROLE_LABEL).map(([value, label]) => ({ value, label }));

export default function UsersTab() {
  const { data: me } = useMe();
  const [search, setSearch] = useState('');
  const [debounced] = useDebouncedValue(search, 300);
  const [role, setRole] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const users = useAdminUsers({ search: debounced, role, active, page });
  const update = useUpdateUser();
  const remove = useDeleteUser();
  const [toDelete, setToDelete] = useState<User | null>(null);

  const fail = (e: Error) => notifications.show({ color: 'red', title: 'Не удалось выполнить действие', message: e.message });
  const rows = users.data?.items ?? [];
  const pages = Math.max(1, Math.ceil((users.data?.total ?? 0) / (users.data?.page_size ?? 15)));

  const columns: Column<User>[] = [
    { key: 'email', header: 'Email', render: (u) => <><Text size="sm" fw={500}>{u.email}</Text><Text size="xs" c="dimmed">{u.full_name || '—'}</Text></> },
    {
      key: 'role', header: 'Роль',
      render: (u) => (
        <Select
          size="xs" w={170} data={ROLE_OPTIONS} value={u.role} allowDeselect={false} disabled={u.id === me?.id}
          aria-label={`Роль пользователя ${u.email}`}
          onChange={(v) => v && v !== u.role && update.mutate({ id: u.id, role: v }, { onError: fail, onSuccess: () => notifications.show({ color: 'teal', message: `Роль изменена: ${ROLE_LABEL[v]}` }) })}
        />
      ),
    },
    {
      key: 'active', header: 'Активен',
      render: (u) => (
        <Switch
          checked={u.is_active} disabled={u.id === me?.id} aria-label={`Доступ пользователя ${u.email}`}
          onChange={(e) => update.mutate({ id: u.id, is_active: e.currentTarget.checked }, { onError: fail })}
        />
      ),
    },
    { key: 'created', header: 'Создан', render: (u) => fmtDateTime(u.created_at) },
    { key: 'login', header: 'Последний вход', render: (u) => fmtDateTime(u.last_login_at) },
    {
      key: 'del', header: '', align: 'right',
      render: (u) => (
        <ActionIcon color="red" variant="subtle" disabled={u.id === me?.id} aria-label={`Удалить пользователя ${u.email}`} onClick={() => setToDelete(u)}>
          <IconTrash size={16} />
        </ActionIcon>
      ),
    },
  ];

  return (
    <Stack gap="md">
      <Paper p="md">
        <Group align="flex-end" gap="md" wrap="wrap">
          <TextInput label="Поиск" placeholder="Email или имя" leftSection={<IconSearch size={16} />} value={search} onChange={(e) => { setSearch(e.currentTarget.value); setPage(1); }} w={260} />
          <Select label="Роль" placeholder="Все" data={ROLE_OPTIONS} value={role} onChange={(v) => { setRole(v); setPage(1); }} clearable w={190} />
          <Select label="Статус" placeholder="Все" data={[{ value: 'true', label: 'Активные' }, { value: 'false', label: 'Заблокированные' }]} value={active} onChange={(v) => { setActive(v); setPage(1); }} clearable w={190} />
          <Text size="sm" c="dimmed">Найдено: {users.data?.total ?? '…'}</Text>
        </Group>
      </Paper>
      {users.error && <ErrorNote error={users.error} />}
      <Paper p="md">
        <SortableTable rows={rows} columns={columns} rowKey={(u) => u.id} minWidth={860} emptyText="Пользователи не найдены" />
        {pages > 1 && <Group justify="center" mt="md"><Pagination total={pages} value={page} onChange={setPage} size="sm" /></Group>}
      </Paper>
      <Text size="xs" c="dimmed">Свою учётную запись нельзя понизить, заблокировать или удалить. Изменения ролей и блокировка действуют немедленно.</Text>

      <Modal opened={!!toDelete} onClose={() => setToDelete(null)} title="Удалить пользователя?" centered>
        <Stack>
          <Text size="sm">Будет удалена учётная запись <b>{toDelete?.email}</b> вместе с её сохранёнными наборами фильтров. Записи журнала сохранятся. Действие необратимо.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setToDelete(null)}>Отмена</Button>
            <Button color="red" loading={remove.isPending} onClick={() => toDelete && remove.mutate(toDelete.id, { onSuccess: () => { setToDelete(null); notifications.show({ color: 'teal', message: 'Пользователь удалён' }); }, onError: fail })}>Удалить</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
