import { Skeleton } from '@mantine/core';
import type { Kpi } from '../api/types';
import type { Filters } from '../filters';
import { fmtHour, fmtInt, fmtMin, fmtPct } from '../utils/format';

function Cell({ label, value, sub, amber }: { label: string; value: string; sub?: string; amber?: boolean }) {
  return (
    <div className="board-cell">
      <div className="board-label">{label}</div>
      <div className={`board-value${amber ? ' amber' : ''}`}>{value}</div>
      {sub && <div className="board-sub">{sub}</div>}
    </div>
  );
}

/** Табло ключевых показателей: число рейсов, доля задержанных, средняя задержка, самый проблемный час. */
export function KpiBoard({ kpi, filters }: { kpi: Kpi | undefined; filters: Filters }) {
  if (!kpi) return <Skeleton height={112} radius={4} />;
  const thr = filters.threshold === 0 ? '> 0 мин' : '≥ 15 мин';
  return (
    <div className="board" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' }} role="region" aria-label="Ключевые показатели">
      <Cell label="Выполнено рейсов" value={fmtInt(kpi.flights)} sub={`отменено ${fmtInt(kpi.cancelled)}, перенаправлено ${fmtInt(kpi.diverted)}`} />
      <Cell label={`Задержано (${thr})`} value={fmtPct(kpi.share)} amber sub={`95% ДИ ${fmtPct(kpi.ci_low)} – ${fmtPct(kpi.ci_high)}`} />
      <Cell
        label={filters.avgMode === 'all' ? 'Средняя задержка, все рейсы' : `Средняя задержка среди задержанных (${thr})`}
        value={fmtMin(kpi.avg_delay)} sub={`максимум ${fmtInt(kpi.max_delay)} мин`}
      />
      <Cell
        label="Самый проблемный час вылета"
        value={kpi.worst_hour ? fmtHour(kpi.worst_hour.hour) : '—'}
        sub={kpi.worst_hour && kpi.best_hour ? `${fmtPct(kpi.worst_hour.share)} задержано; лучший час — ${fmtHour(kpi.best_hour.hour)} (${fmtPct(kpi.best_hour.share)})` : undefined}
        amber
      />
    </div>
  );
}
