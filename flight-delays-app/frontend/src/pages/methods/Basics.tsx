import { Badge, Text } from '@mantine/core';
import type { StatTest } from '../../api/types';
import { fmtNum } from '../../utils/format';

export const EFFECT_COLOR: Record<string, string> = {
  'практически отсутствует': 'gray', незначительная: 'gray', незначительный: 'gray',
  слабая: 'yellow', малый: 'yellow', умеренная: 'orange', средний: 'orange', заметная: 'orange',
  сильная: 'red', большой: 'red',
};

export const EffectBadge = ({ label }: { label: string }) => (
  <Badge variant="light" color={EFFECT_COLOR[label] ?? 'gray'} radius="sm">{label}</Badge>
);

export const effectText = (t: StatTest) => `${t.effect_name} = ${fmtNum(t.effect_value, 3)}`;

export function Note({ children }: { children: React.ReactNode }) {
  return <Text size="sm" c="dimmed" maw={820}>{children}</Text>;
}

export interface BoardItem { label: string; value: string; sub?: string; amber?: boolean }

/** Тёмное «табло» с числами — тот же элемент, что и на панели показателей. */
export function Board({ items }: { items: BoardItem[] }) {
  return (
    <div className="board" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' }}>
      {items.map((i) => (
        <div className="board-cell" key={i.label}>
          <div className="board-label">{i.label}</div>
          <div className={`board-value${i.amber ? ' amber' : ''}`}>{i.value}</div>
          {i.sub && <div className="board-sub">{i.sub}</div>}
        </div>
      ))}
    </div>
  );
}
