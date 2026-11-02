import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, del, get, patch, post } from './client';
import type {
  AirlineRow, AirportRow, AuditRecord, CategoryRow, CompareOut, DataInfo, DunnRow, FilterOptions, HeatCell,
  Highlights, HourRow, Kpi, MethodsSummary, MonthRow, Page, PeriodRow, Regression, SavedFilter, SavedParams, User,
  AirlineOpt, AirportOpt,
} from './types';
import { Filters, filtersToParams } from '../filters';

const FIVE_MIN = 5 * 60_000;

// ───────── Сессия ─────────
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await get<User | null>('/auth/session'); // null — гость
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: Infinity,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: { email: string; password: string }) => post<User>('/auth/login', b),
    onSuccess: (user) => { qc.clear(); qc.setQueryData(['me'], user); },
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: { email: string; password: string; full_name: string }) => post<User>('/auth/register', b),
    onSuccess: (user) => { qc.clear(); qc.setQueryData(['me'], user); },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => post<void>('/auth/logout'),
    onSettled: () => { qc.clear(); qc.setQueryData(['me'], null); },
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (full_name: string) => patch<User>('/auth/me', { full_name }),
    onSuccess: (user) => qc.setQueryData(['me'], user),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (b: { current_password: string; new_password: string }) => post<User>('/auth/change-password', b),
  });
}

// ───────── Публичные данные и справочники ─────────
export const useHighlights = () =>
  useQuery({ queryKey: ['highlights'], queryFn: () => get<Highlights>('/public/highlights'), staleTime: FIVE_MIN });

export const useFilterOptions = (enabled = true) =>
  useQuery({ queryKey: ['filter-options'], queryFn: () => get<FilterOptions>('/meta/filters'), staleTime: FIVE_MIN, enabled });

// ───────── Статистика ─────────
type Extra = Record<string, string | number>;

function useStat<T>(path: string, f: Filters, extra: Extra = {}, opts: { omitAirlines?: boolean; enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ['stats', path, f, extra, opts.omitAirlines ?? false],
    queryFn: () => {
      const params = filtersToParams(f, { omitAirlines: opts.omitAirlines });
      Object.entries(extra).forEach(([k, v]) => params.set(k, String(v)));
      return get<T>(`/stats/${path}`, params);
    },
    placeholderData: keepPreviousData,
    staleTime: FIVE_MIN,
    enabled: opts.enabled ?? true,
  });
}

export const useKpi = (f: Filters) => useStat<Kpi>('kpi', f);
export const useHourly = (f: Filters) => useStat<HourRow[]>('hourly', f);
export const usePeriods = (f: Filters) => useStat<PeriodRow[]>('periods', f);
export const useHeatmap = (f: Filters) => useStat<HeatCell[]>('heatmap', f);
export const useMonthly = (f: Filters) => useStat<MonthRow[]>('monthly', f);
export const useAirlines = (f: Filters) => useStat<AirlineRow[]>('airlines', f);
export const useCategories = (f: Filters) => useStat<CategoryRow[]>('categories', f);
export const useAirports = (f: Filters, sort: string, order: string, minFlights: number, limit: number) =>
  useStat<AirportRow[]>('airports', f, { sort, order, min_flights: minFlights, limit });
export const useCompare = (f: Filters, a: number | null, b: number | null) =>
  useStat<CompareOut>('compare', f, { airline_a: a ?? 0, airline_b: b ?? 0 }, { omitAirlines: true, enabled: !!a && !!b && a !== b });

// ───────── Методы анализа (аналитик) ─────────
export const useMethodsSummary = () => useQuery({ queryKey: ['methods', 'summary'], queryFn: () => get<MethodsSummary>('/methods/summary'), staleTime: Infinity });
export const useDunn = () => useQuery({ queryKey: ['methods', 'dunn'], queryFn: () => get<DunnRow[]>('/methods/dunn'), staleTime: Infinity });
export const useRegression = () => useQuery({ queryKey: ['methods', 'regression'], queryFn: () => get<Regression>('/methods/regression'), staleTime: Infinity });

// ───────── Сохранённые фильтры (аналитик) ─────────
export const useSavedFilters = (enabled: boolean) =>
  useQuery({ queryKey: ['saved-filters'], queryFn: () => get<SavedFilter[]>('/saved-filters'), enabled });

export function useSaveFilter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: { name: string; params: SavedParams }) => post<SavedFilter>('/saved-filters', b),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved-filters'] }),
  });
}

export function useDeleteSavedFilter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => del(`/saved-filters/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved-filters'] }),
  });
}

// ───────── Администрирование ─────────
export const useAdminUsers = (p: { search: string; role: string | null; active: string | null; page: number }) =>
  useQuery({
    queryKey: ['admin', 'users', p],
    queryFn: () => get<Page<User>>('/admin/users', { search: p.search, role: p.role, active: p.active, page: p.page, page_size: 15 }),
    placeholderData: keepPreviousData,
  });

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; role?: string; is_active?: boolean }) => patch<User>(`/admin/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => del(`/admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  });
}

export const useAudit = (p: { action: string | null; email: string; dateFrom: string; dateTo: string; page: number }) =>
  useQuery({
    queryKey: ['admin', 'audit', p],
    queryFn: () => get<Page<AuditRecord>>('/admin/audit', {
      action: p.action, email: p.email, date_from: p.dateFrom, date_to: p.dateTo, page: p.page, page_size: 20,
    }),
    placeholderData: keepPreviousData,
  });

export const useAdminAirlines = () => useQuery({ queryKey: ['admin', 'airlines'], queryFn: () => get<AirlineOpt[]>('/admin/airlines') });
export const useAdminAirports = (search: string, page: number) =>
  useQuery({
    queryKey: ['admin', 'airports', search, page],
    queryFn: () => get<Page<AirportOpt>>('/admin/airports', { search, page, page_size: 15 }),
    placeholderData: keepPreviousData,
  });

export function useUpdateAirline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => patch<AirlineOpt>(`/admin/airlines/${id}`, { name }),
    onSuccess: () => { qc.invalidateQueries(); },
  });
}

export function useUpdateAirport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; name: string; city: string; state: string }) => patch<AirportOpt>(`/admin/airports/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(); },
  });
}

export const useDataInfo = () => useQuery({ queryKey: ['admin', 'data'], queryFn: () => get<DataInfo>('/admin/data') });
