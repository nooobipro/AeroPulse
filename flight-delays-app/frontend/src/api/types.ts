export type Role = 'user' | 'analyst' | 'admin';

export interface User {
  id: number; email: string; full_name: string; role: Role; is_active: boolean;
  created_at: string; last_login_at: string | null;
}

export interface Rate {
  flights: number; delayed: number; share: number | null;
  ci_low: number | null; ci_high: number | null; avg_delay: number | null;
}
export interface HourRef { hour: number; share: number; flights: number }
export interface Kpi extends Rate {
  cancelled: number; diverted: number; max_delay: number; worst_hour: HourRef | null; best_hour: HourRef | null;
}
export interface AirlineRow extends Rate { airline_id: number; code: string; name: string; max_delay: number }
export interface HourRow extends Rate { hour: number }
export interface PeriodRow extends Rate { code: string; label: string; hour_from: number; hour_to: number }
export interface HeatCell { dow: number; hour: number; flights: number; delayed: number; share: number | null; reliable: boolean }
export interface AirportRow extends Rate { airport_id: number; code: string; name: string; city: string; state: string }
export interface CategoryRow { key: string; label: string; flights: number; share: number | null }
export interface MonthRow extends Rate { period: string }
export interface CompareSide { airline_id: number; name: string; kpi: Kpi; hourly: HourRow[]; categories: CategoryRow[] }
export interface CompareDiff { diff: number; ci_low: number; ci_high: number; p_value: number; risk_ratio: number | null }
export interface CompareOut { a: CompareSide; b: CompareSide; diff: CompareDiff | null }

export interface AirlineOpt { id: number; code: string; name: string }
export interface AirportOpt { id: number; code: string; name: string; city: string; state: string }
export interface DataVersion {
  id: number; loaded_at: string; period_start: string; period_end: string; rows_total: number; rows_used: number;
  airlines: number; airports: number; is_demo: boolean; source: string; notes: Record<string, any> | null;
}
export interface FilterOptions { airlines: AirlineOpt[]; airports: AirportOpt[]; periods: string[]; data: DataVersion | null }

export interface PeriodShare { code: string; label: string; hour_from: number; hour_to: number; share: number | null; flights: number }
export interface ShareRef { name: string; share: number; flights: number }
export interface Highlights {
  has_data: boolean; is_demo: boolean; flights: number; airlines: number; airports: number;
  period_start: string | null; period_end: string | null; share: number | null; share15: number | null;
  periods: PeriodShare[]; hourly: { hour: number; share: number; flights: number }[];
  best_airline: ShareRef | null; worst_airline: ShareRef | null;
}

export interface StatTest {
  code: string; family: string; title: string; statistic: number | null; dof: number | null; p_value: number | null;
  effect_name: string; effect_value: number | null; effect_ci_low: number | null; effect_ci_high: number | null;
  effect_label: string; n: number; details: Record<string, any> | null;
}
export interface MethodsSummary { spearman: StatTest[]; chi2: StatTest[]; kruskal: StatTest[]; sample: Record<string, any> | null }
export interface DunnRow {
  airline_a_id: number; airline_a: string; airline_b_id: number; airline_b: string;
  z: number; p_value: number; p_adj: number; significant: boolean;
}
export interface Coef {
  model: string; grp: string; term: string; label: string; estimate: number; std_error: number | null;
  ci_low: number | null; ci_high: number | null; p_value: number | null;
  odds_ratio: number | null; or_ci_low: number | null; or_ci_high: number | null;
}
export interface ModelBlock {
  code: string; title: string; target: string; kind: 'linear' | 'logit'; coefficients: Coef[];
  metrics: Record<string, number | null>;
}
export interface Regression {
  models: ModelBlock[]; hour_stability: Coef[];
  hour_probability: { hours: number[]; adjusted: number[]; observed: (number | null)[] } | null;
  calibration: { bin: number; predicted: number; observed: number; n: number }[] | null;
  sample: Record<string, any> | null;
}

export interface SavedParams {
  airline_id: number[]; airport_id: number[]; period_from: string | null; period_to: string | null;
  hour_from: number; hour_to: number; threshold: 0 | 15; avg_mode: 'all' | 'delayed';
}
export interface SavedFilter { id: number; name: string; params: SavedParams; created_at: string }

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface AuditRecord { id: number; created_at: string; user_id: number | null; user_email: string; action: string; details: string; ip: string }
export interface DataInfo { current: DataVersion | null; history: DataVersion[]; counts: Record<string, number> }
