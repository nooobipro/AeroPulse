import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import App from '../App';
import { theme } from '../theme';
import fixtures from './fixtures.json';

export const fx = fixtures as Record<string, any>;
export type TestRole = 'guest' | 'user' | 'analyst' | 'admin';

/** Подменяет fetch: ответы — реальные снимки API (fixtures.json), снятые с работающего бэкенда. */
export function mockApi(initial: TestRole) {
  const state = { role: initial };
  const calls: string[] = [];
  const respond = (body: unknown, status = 200) =>
    new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const path = url.pathname.replace(/^\/api/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    calls.push(`${method} ${path}${url.search}`);

    if (method === 'POST' && path === '/auth/login') {
      const body = JSON.parse(String(init?.body));
      if (body.password !== 'Passw0rd123') return respond({ detail: 'Неверный email или пароль' }, 401);
      state.role = 'analyst';
      return respond(fx.me_analyst);
    }
    if (method === 'POST' && path === '/auth/logout') { state.role = 'guest'; return respond(null, 204); }
    const routes: Record<string, unknown> = {
      '/auth/session': state.role === 'guest' ? null : fx[`me_${state.role}`],
      '/public/highlights': fx.highlights, '/meta/filters': fx.filters,
      '/stats/kpi': fx.kpi, '/stats/airlines': fx.airlines, '/stats/hourly': fx.hourly, '/stats/periods': fx.periods,
      '/stats/heatmap': fx.heatmap, '/stats/monthly': fx.monthly, '/stats/airports': fx.airports,
      '/stats/categories': fx.categories, '/stats/compare': fx.compare,
      '/methods/summary': fx.methods_summary, '/methods/dunn': fx.dunn, '/methods/regression': fx.regression,
      '/saved-filters': fx.saved_filters,
      '/admin/users': fx.admin_users, '/admin/audit': fx.admin_audit, '/admin/airlines': fx.admin_airlines,
      '/admin/airports': fx.admin_airports, '/admin/data': fx.admin_data,
    };
    return path in routes ? respond(routes[path]) : respond({ detail: `нет заглушки для ${path}` }, 404);
  }));
  return { calls, state };
}

export function renderApp(path: string, role: TestRole) {
  const api = mockApi(role);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  const view = render(
    <MantineProvider theme={theme}>
      <Notifications />
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}><App /></MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
  return { ...view, ...api };
}
