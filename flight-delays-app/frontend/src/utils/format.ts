const nf = new Intl.NumberFormat('ru-RU');
const nf1 = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf3 = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export const DASH = '—';
export const fmtInt = (n: number | null | undefined) => (n == null ? DASH : nf.format(Math.round(n)));
export const fmtPct = (x: number | null | undefined, digits = 1) =>
  x == null ? DASH : `${(digits === 0 ? nf : nf1).format(digits === 0 ? Math.round(x * 100) : x * 100)} %`;
export const fmtMin = (x: number | null | undefined) => (x == null ? DASH : `${nf1.format(x)} мин`);
export const fmtNum = (x: number | null | undefined, digits: 1 | 2 | 3 = 2) =>
  x == null || Number.isNaN(x) ? DASH : (digits === 1 ? nf1 : digits === 2 ? nf2 : nf3).format(x);
export const fmtHour = (h: number) => `${String(h).padStart(2, '0')}:00`;
export const fmtP = (p: number | null | undefined) => (p == null ? DASH : p < 0.001 ? '< 0,001' : nf3.format(p));
export const fmtDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : DASH;
export const fmtSigned = (x: number | null | undefined, digits: 1 | 2 | 3 = 2) =>
  x == null ? DASH : `${x > 0 ? '+' : ''}${fmtNum(x, digits)}`;

export const DOW = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
export const fmtPeriod = (p: string) => {
  const [y, m] = p.split('-');
  return `${MONTHS[Number(m) - 1]} ${y}`;
};
export const round = (x: number, d = 1) => Math.round(x * 10 ** d) / 10 ** d;

export const ROLE_LABEL: Record<string, string> = { user: 'Пользователь', analyst: 'Аналитик', admin: 'Администратор' };
export const ROLE_RANK: Record<string, number> = { user: 1, analyst: 2, admin: 3 };

export const ACTION_LABEL: Record<string, string> = {
  register: 'Регистрация', login: 'Вход', login_failed: 'Неудачный вход', login_blocked: 'Вход заблокирован (лимит попыток)',
  profile_update: 'Изменение профиля', password_change: 'Смена пароля', password_change_failed: 'Неудачная смена пароля',
  export_xlsx: 'Экспорт в Excel', export_pdf: 'Экспорт в PDF', export_csv: 'Экспорт в CSV',
  saved_filter_create: 'Сохранение набора фильтров', saved_filter_delete: 'Удаление набора фильтров',
  admin_user_update: 'Изменение пользователя', admin_user_delete: 'Удаление пользователя',
  admin_airline_update: 'Правка авиакомпании', admin_airport_update: 'Правка аэропорта',
};
