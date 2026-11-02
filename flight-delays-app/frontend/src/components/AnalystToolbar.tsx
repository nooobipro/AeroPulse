import { ActionIcon, Button, Group, Menu, Modal, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconBookmark, IconChevronDown, IconDeviceFloppy, IconFileSpreadsheet, IconFileTypePdf, IconTableExport, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { downloadFile } from '../api/client';
import { useDeleteSavedFilter, useSaveFilter, useSavedFilters } from '../api/hooks';
import { Filters, filtersFromSaved, filtersToParams, filtersToSaved } from '../filters';

const DATASETS: [string, string][] = [
  ['airlines', 'Авиакомпании'], ['hourly', 'По часам вылета'], ['periods', 'Периоды суток'], ['airports', 'Аэропорты вылета'],
  ['categories', 'Категории задержек'], ['heatmap', 'День недели × час'], ['monthly', 'По месяцам'],
];

/** Инструменты аналитика: сохранённые наборы фильтров, отчёты Excel/PDF, выгрузка таблиц в CSV. */
export function AnalystToolbar({ filters, onApply }: { filters: Filters; onApply: (f: Filters) => void }) {
  const saved = useSavedFilters(true);
  const save = useSaveFilter();
  const remove = useDeleteSavedFilter();
  const [modal, setModal] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (key: string, path: string, extra: Record<string, string>) => {
    setBusy(key);
    const params = filtersToParams(filters);
    Object.entries(extra).forEach(([k, v]) => params.set(k, v));
    try {
      await downloadFile(path, params);
    } finally {
      setBusy(null);
    }
  };

  const submit = () => {
    setError(null);
    save.mutate({ name, params: filtersToSaved(filters) }, {
      onSuccess: () => { setModal(false); setName(''); notifications.show({ color: 'teal', message: 'Набор фильтров сохранён' }); },
      onError: (e) => setError(e.message),
    });
  };

  return (
    <>
      <Group gap="xs" wrap="wrap">
        <Menu position="bottom-end" width={290}>
          <Menu.Target>
            <Button variant="default" size="xs" leftSection={<IconBookmark size={16} />} rightSection={<IconChevronDown size={14} />}>
              Сохранённые наборы{saved.data?.length ? ` (${saved.data.length})` : ''}
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            {saved.data?.length ? saved.data.map((s) => (
              <Menu.Item
                key={s.id} onClick={() => onApply(filtersFromSaved(s.params))}
                rightSection={
                  <ActionIcon
                    size="sm" variant="subtle" color="red" aria-label={`Удалить набор ${s.name}`}
                    onClick={(e) => { e.stopPropagation(); remove.mutate(s.id); }}
                  ><IconTrash size={14} /></ActionIcon>
                }
              >{s.name}</Menu.Item>
            )) : <Text size="sm" c="dimmed" px="sm" py={6}>Пока нет сохранённых наборов</Text>}
            <Menu.Divider />
            <Menu.Item leftSection={<IconDeviceFloppy size={16} />} onClick={() => setModal(true)}>Сохранить текущие фильтры…</Menu.Item>
          </Menu.Dropdown>
        </Menu>

        <Menu position="bottom-end" width={230}>
          <Menu.Target>
            <Button variant="default" size="xs" loading={busy === 'xlsx' || busy === 'pdf'} leftSection={<IconFileSpreadsheet size={16} />} rightSection={<IconChevronDown size={14} />}>
              Отчёт
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>С учётом текущих фильтров</Menu.Label>
            <Menu.Item leftSection={<IconFileSpreadsheet size={16} />} onClick={() => run('xlsx', '/reports/export', { format: 'xlsx' })}>Excel (.xlsx) с графиками</Menu.Item>
            <Menu.Item leftSection={<IconFileTypePdf size={16} />} onClick={() => run('pdf', '/reports/export', { format: 'pdf' })}>PDF с графиками</Menu.Item>
          </Menu.Dropdown>
        </Menu>

        <Menu position="bottom-end" width={230}>
          <Menu.Target>
            <Button variant="default" size="xs" loading={busy?.startsWith('csv') ?? false} leftSection={<IconTableExport size={16} />} rightSection={<IconChevronDown size={14} />}>
              Таблицы CSV
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Label>Агрегированные таблицы</Menu.Label>
            {DATASETS.map(([key, label]) => (
              <Menu.Item key={key} onClick={() => run(`csv-${key}`, '/reports/csv', { dataset: key })}>{label}</Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>
      </Group>

      <Modal opened={modal} onClose={() => setModal(false)} title="Сохранить набор фильтров" centered>
        <Stack>
          <TextInput
            label="Название" placeholder="Например: утренние рейсы, порог 15 минут" value={name} maxLength={60} data-autofocus
            onChange={(e) => setName(e.currentTarget.value)} error={error}
            onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) submit(); }}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setModal(false)}>Отмена</Button>
            <Button onClick={submit} loading={save.isPending} disabled={!name.trim()}>Сохранить</Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
