import { fireEvent, screen, waitFor, within } from '@testing-library/react';

const formButton = (name: string) => within(document.querySelector('form') as HTMLElement).getByRole('button', { name });
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fx, renderApp } from './helpers';

// Canvas в jsdom недоступен: график заменяется заглушкой, по которой проверяем, что опция построена
vi.mock('../components/Chart', () => ({
  Chart: ({ option }: { option: { series?: unknown[] } | null }) => <div data-testid="chart" data-series={option?.series?.length ?? 0} />,
}));

afterEach(() => vi.unstubAllGlobals());

describe('гость', () => {
  it('видит лендинг: табло по часам и выводы, посчитанные из данных', async () => {
    renderApp('/', 'guest');
    expect(await screen.findByText(/Насколько пунктуальны рейсы/)).toBeInTheDocument();
    expect(await screen.findByText(/Утром \(/)).toBeInTheDocument();
    expect(screen.getByText(/Демонстрационный режим/)).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Табло/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Создать аккаунт' })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('link', { name: 'Панель' })).not.toBeInTheDocument();
  });

  it('перенаправляется на вход при попытке открыть закрытые разделы', async () => {
    renderApp('/dashboard', 'guest');
    expect(await screen.findByRole('heading', { name: 'Вход' })).toBeInTheDocument();
  });

  it('входит и попадает на панель с показателями', async () => {
    renderApp('/login', 'guest');
    fireEvent.change(await screen.findByLabelText(/Email/), { target: { value: 'analyst@example.com' } });
    fireEvent.change(document.querySelector('input[type=password]')!, { target: { value: 'Passw0rd123' } });
    fireEvent.click(formButton('Войти'));
    expect(await screen.findByRole('heading', { name: 'Панель показателей' })).toBeInTheDocument();
  });

  it('видит понятную ошибку при неверном пароле', async () => {
    renderApp('/login', 'guest');
    fireEvent.change(await screen.findByLabelText(/Email/), { target: { value: 'analyst@example.com' } });
    fireEvent.change(document.querySelector('input[type=password]')!, { target: { value: 'wrong-pass-1' } });
    fireEvent.click(formButton('Войти'));
    expect(await screen.findByText('Неверный email или пароль')).toBeInTheDocument();
  });

  it('форма регистрации проверяет совпадение паролей до отправки', async () => {
    const { calls } = renderApp('/register', 'guest');
    fireEvent.change(await screen.findByLabelText(/Email/), { target: { value: 'new@example.com' } });
    const [pw, repeat] = Array.from(document.querySelectorAll('input[type=password]'));
    fireEvent.change(pw, { target: { value: 'Passw0rd123' } });
    fireEvent.change(repeat, { target: { value: 'Different123' } });
    fireEvent.click(formButton('Создать аккаунт'));
    expect(await screen.findByText('Пароли не совпадают')).toBeInTheDocument();
    expect(calls.some((c) => c.startsWith('POST /auth/register'))).toBe(false);
  });
});

describe('пользователь', () => {
  it('видит панель, но не инструменты аналитика и не методы анализа', async () => {
    renderApp('/dashboard', 'user');
    expect(await screen.findByText('3 930 204')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Отчёт/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Методы анализа' })).not.toBeInTheDocument();
  });

  it('получает отказ на разделах аналитика и администратора', async () => {
    const view = renderApp('/methods', 'user');
    expect(await screen.findByText('Недостаточно прав')).toBeInTheDocument();
    view.unmount();
    renderApp('/admin', 'user');
    expect(await screen.findByText('Недостаточно прав')).toBeInTheDocument();
  });
});

describe('панель показателей', () => {
  it('показывает табло, графики и таблицы на всех вкладках', async () => {
    renderApp('/dashboard', 'analyst');
    expect(await screen.findByText('3 930 204')).toBeInTheDocument();
    expect(screen.getByText('37,2 %')).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId('chart').length).toBe(4)); // часы, периоды, месяцы, тепловая карта

    fireEvent.click(screen.getByRole('tab', { name: /Авиакомпании/ }));
    const row = (await screen.findAllByText('Glacier Air'))[0];
    expect(row).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Доля задержанных/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Аэропорты/ }));
    expect(await screen.findByText(fx.airports[0].code)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Категории задержек/ }));
    expect(await screen.findByText('Более 120 минут')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Сравнение авиакомпаний/ }));
    expect(await screen.findByText('Различие в доле задержанных рейсов')).toBeInTheDocument();
  });

  it('читает фильтры из адресной строки и передаёт их в запросы', async () => {
    const { calls } = renderApp('/dashboard?airline_id=2&airline_id=1&hour_from=6&hour_to=12&threshold=15&avg_mode=delayed', 'analyst');
    expect(await screen.findByText('3 930 204')).toBeInTheDocument();
    const kpi = calls.find((c) => c.startsWith('GET /stats/kpi'))!;
    expect(kpi).toContain('airline_id=1&airline_id=2');
    expect(kpi).toContain('hour_from=6');
    expect(kpi).toContain('hour_to=12');
    expect(kpi).toContain('threshold=15');
    expect(kpi).toContain('avg_mode=delayed');
  });

  it('аналитик видит отчёты, CSV и сохранённые наборы', async () => {
    renderApp('/dashboard', 'analyst');
    await screen.findByText('3 930 204');
    expect(screen.getByRole('button', { name: /Отчёт/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Таблицы CSV/ })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /Сохранённые наборы/ })).toBeInTheDocument();
  });
});

describe('методы анализа', () => {
  it('показывает результаты регрессии с метриками качества', async () => {
    renderApp('/methods', 'analyst');
    expect(await screen.findByText('AUC на проверочной выборке')).toBeInTheDocument();
    expect(await screen.findByText('Время вылета при прочих равных')).toBeInTheDocument();
    expect(screen.getByText('Авиакомпании при прочих равных')).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId('chart').length).toBeGreaterThanOrEqual(4));
  });

  it('вкладки корреляций, хи-квадрат, Краскела — Уоллиса и ограничений', async () => {
    renderApp('/methods', 'analyst');
    await screen.findByText('AUC на проверочной выборке');
    fireEvent.click(screen.getByRole('tab', { name: /Корреляции/ }));
    expect(await screen.findByText(/Час вылета и задержка прибытия/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Хи-квадрат/ }));
    expect((await screen.findAllByText('V Крамера')).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('tab', { name: /Краскел/ }));
    expect(await screen.findByText('Парные сравнения Данна')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Ограничения/ }));
    expect(await screen.findByText(/Связь — не причина/)).toBeInTheDocument();
  });

  it('аналитик не попадает в администрирование', async () => {
    renderApp('/admin', 'analyst');
    expect(await screen.findByText('Недостаточно прав')).toBeInTheDocument();
  });
});

describe('администратор', () => {
  it('видит пользователей, журнал, справочники и сведения о данных', async () => {
    renderApp('/admin', 'admin');
    const email = fx.admin_users.items[0].email;
    expect((await screen.findAllByText(email))[0]).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Журнал действий' }));
    expect(await screen.findByText('Подробности')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Справочники' }));
    expect(await screen.findByText('Отображаемое название')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Данные' }));
    expect(await screen.findByText('Период данных')).toBeInTheDocument();
    expect(screen.getByText('демонстрационные данные')).toBeInTheDocument();
  });

  it('не позволяет менять собственную роль и удалять себя', async () => {
    renderApp('/admin', 'admin');
    const selfRow = (await screen.findAllByText(fx.me_admin.email))[0].closest('tr') as HTMLElement;
    expect(within(selfRow).getByRole('button', { name: new RegExp(`Удалить пользователя ${fx.me_admin.email}`) })).toBeDisabled();
    expect(within(selfRow).getByRole('switch')).toBeDisabled();
  });
});
