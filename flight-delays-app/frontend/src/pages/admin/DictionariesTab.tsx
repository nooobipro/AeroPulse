import { Button, Group, Modal, Pagination, Paper, Stack, Tabs, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useState } from 'react';
import { useAdminAirlines, useAdminAirports, useUpdateAirline, useUpdateAirport } from '../../api/hooks';
import type { AirlineOpt, AirportOpt } from '../../api/types';
import { ErrorNote, PageLoader } from '../../components/common';
import { Column, SortableTable } from '../../components/SortableTable';

function AirlineNameCell({ airline }: { airline: AirlineOpt }) {
  const update = useUpdateAirline();
  const [name, setName] = useState(airline.name);
  const dirty = name.trim() !== airline.name && name.trim().length > 0;
  return (
    <Group gap="xs" wrap="nowrap">
      <TextInput size="xs" value={name} maxLength={150} onChange={(e) => setName(e.currentTarget.value)} w={320} aria-label={`Название авиакомпании ${airline.code}`} />
      <Button
        size="xs" disabled={!dirty} loading={update.isPending}
        onClick={() => update.mutate({ id: airline.id, name: name.trim() }, {
          onSuccess: () => notifications.show({ color: 'teal', message: 'Название сохранено' }),
          onError: (e) => notifications.show({ color: 'red', message: e.message }),
        })}
      >Сохранить</Button>
    </Group>
  );
}

function Airlines() {
  const { data, error } = useAdminAirlines();
  if (error) return <ErrorNote error={error} />;
  if (!data) return <PageLoader />;
  const columns: Column<AirlineOpt>[] = [
    { key: 'code', header: 'Код в исходных данных', render: (a) => a.code, sortValue: (a) => a.code },
    { key: 'name', header: 'Отображаемое название', render: (a) => <AirlineNameCell key={`${a.id}-${a.name}`} airline={a} /> },
  ];
  return <Paper p="md"><SortableTable rows={data} columns={columns} rowKey={(a) => a.id} minWidth={640} /></Paper>;
}

function Airports() {
  const [search, setSearch] = useState('');
  const [debounced] = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const { data, error } = useAdminAirports(debounced, page);
  const update = useUpdateAirport();
  const [edit, setEdit] = useState<AirportOpt | null>(null);
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 15)));

  const columns: Column<AirportOpt>[] = [
    { key: 'code', header: 'Код', render: (a) => <b>{a.code}</b> },
    { key: 'name', header: 'Название аэропорта', render: (a) => a.name || '—' },
    { key: 'city', header: 'Город', render: (a) => a.city || '—' },
    { key: 'state', header: 'Штат', render: (a) => a.state || '—' },
    { key: 'edit', header: '', align: 'right', render: (a) => <Button size="xs" variant="default" onClick={() => setEdit(a)}>Изменить</Button> },
  ];

  return (
    <Stack gap="md">
      <TextInput label="Поиск" placeholder="Код, название или город" value={search} onChange={(e) => { setSearch(e.currentTarget.value); setPage(1); }} w={300} />
      {error && <ErrorNote error={error} />}
      <Paper p="md">
        <SortableTable rows={data?.items ?? []} columns={columns} rowKey={(a) => a.id} minWidth={640} emptyText="Аэропорты не найдены" />
        {pages > 1 && <Group justify="center" mt="md"><Pagination total={pages} value={page} onChange={setPage} size="sm" /></Group>}
      </Paper>
      <Modal opened={!!edit} onClose={() => setEdit(null)} title={`Аэропорт ${edit?.code ?? ''}`} centered>
        {edit && (
          <Stack>
            <TextInput label="Название" value={edit.name} maxLength={150} onChange={(e) => setEdit({ ...edit, name: e.currentTarget.value })} />
            <TextInput label="Город" value={edit.city} maxLength={100} onChange={(e) => setEdit({ ...edit, city: e.currentTarget.value })} />
            <TextInput label="Штат / регион" value={edit.state} maxLength={50} onChange={(e) => setEdit({ ...edit, state: e.currentTarget.value })} />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEdit(null)}>Отмена</Button>
              <Button loading={update.isPending} onClick={() => update.mutate({ id: edit.id, name: edit.name, city: edit.city, state: edit.state }, {
                onSuccess: () => { setEdit(null); notifications.show({ color: 'teal', message: 'Аэропорт обновлён' }); },
                onError: (e) => notifications.show({ color: 'red', message: e.message }),
              })}>Сохранить</Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}

export default function DictionariesTab() {
  return (
    <Stack gap="sm">
      <Text size="sm" c="dimmed" maw={720}>Названия влияют только на отображение: коды из исходных данных не меняются, а правки сохраняются при повторной загрузке данных.</Text>
      <Tabs defaultValue="airlines" keepMounted={false} color="amber.5">
        <Tabs.List><Tabs.Tab value="airlines">Авиакомпании</Tabs.Tab><Tabs.Tab value="airports">Аэропорты</Tabs.Tab></Tabs.List>
        <Tabs.Panel value="airlines" pt="md"><Airlines /></Tabs.Panel>
        <Tabs.Panel value="airports" pt="md"><Airports /></Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
