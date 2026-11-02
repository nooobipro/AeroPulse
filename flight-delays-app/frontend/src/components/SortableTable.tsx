import { Table, Text, UnstyledButton } from '@mantine/core';
import { IconArrowDown, IconArrowUp, IconArrowsSort } from '@tabler/icons-react';
import { ReactNode, useMemo, useState } from 'react';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => number | string | null | undefined;
  align?: 'left' | 'right';
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string | number;
  initialSort?: { key: string; dir: 'asc' | 'desc' };
  minWidth?: number;
  emptyText?: string;
  caption?: string;
}

/** Таблица с сортировкой по клику на заголовок. */
export function SortableTable<T>({ rows, columns, rowKey, initialSort, minWidth = 640, emptyText = 'Нет данных', caption }: Props<T>) {
  const [sort, setSort] = useState(initialSort ?? null);
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort?.key);
    if (!col?.sortValue || !sort) return rows;
    const val = col.sortValue;
    const dir = sort.dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = val(a), y = val(b);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (typeof x === 'string' && typeof y === 'string' ? x.localeCompare(y, 'ru') : (x as number) - (y as number)) * dir;
    });
  }, [rows, columns, sort]);

  const toggle = (key: string) => setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }));

  return (
    <Table.ScrollContainer minWidth={minWidth}>
      <Table striped highlightOnHover withRowBorders>
        {caption && <Table.Caption>{caption}</Table.Caption>}
        <Table.Thead>
          <Table.Tr>
            {columns.map((c) => (
              <Table.Th key={c.key} ta={c.align ?? 'left'} aria-sort={sort?.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}>
                {c.sortValue ? (
                  <UnstyledButton onClick={() => toggle(c.key)} style={{ font: 'inherit', fontWeight: 600 }}>
                    {c.header}{' '}
                    {sort?.key === c.key ? (sort.dir === 'asc' ? <IconArrowUp size={13} /> : <IconArrowDown size={13} />) : <IconArrowsSort size={13} opacity={0.4} />}
                  </UnstyledButton>
                ) : c.header}
              </Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.length === 0 ? (
            <Table.Tr><Table.Td colSpan={columns.length}><Text c="dimmed" ta="center" py="sm">{emptyText}</Text></Table.Td></Table.Tr>
          ) : sorted.map((r) => (
            <Table.Tr key={rowKey(r)}>
              {columns.map((c) => <Table.Td key={c.key} ta={c.align ?? 'left'} className={c.align === 'right' ? 'num' : undefined}>{c.render(r)}</Table.Td>)}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
