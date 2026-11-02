import { notifications } from '@mantine/notifications';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Params = URLSearchParams | Record<string, string | number | boolean | null | undefined | (string | number)[]>;

export function toSearchParams(params?: Params): URLSearchParams {
  if (params instanceof URLSearchParams) return params;
  const sp = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === '') return;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, String(x)));
    else sp.set(k, String(v));
  });
  return sp;
}

function parseDetail(data: any): string | null {
  const d = data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map((e) => String(e.msg ?? '').replace(/^Value error, /, '')).filter(Boolean).join('. ') || null;
  }
  return null;
}

async function request<T>(method: string, path: string, opts: { params?: Params; body?: unknown } = {}): Promise<T> {
  const qs = toSearchParams(opts.params).toString();
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ''}`, {
    method,
    credentials: 'same-origin',
    headers: opts.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, parseDetail(data) ?? `Ошибка ${res.status}`);
  return data as T;
}

export const get = <T,>(path: string, params?: Params) => request<T>('GET', path, { params });
export const post = <T,>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} });
export const patch = <T,>(path: string, body: unknown) => request<T>('PATCH', path, { body });
export const del = <T = void,>(path: string) => request<T>('DELETE', path);

/** Скачивание файла через fetch: ошибки (429, 403…) показываются уведомлением, а не страницей с JSON. */
export async function downloadFile(path: string, params?: Params): Promise<void> {
  const qs = toSearchParams(params).toString();
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ''}`, { credentials: 'same-origin' });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    notifications.show({ color: 'red', title: 'Не удалось сформировать файл', message: parseDetail(data) ?? `Ошибка ${res.status}` });
    return;
  }
  const match = /filename="([^"]+)"/.exec(res.headers.get('content-disposition') ?? '');
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement('a');
  a.href = url;
  a.download = match?.[1] ?? 'report';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
