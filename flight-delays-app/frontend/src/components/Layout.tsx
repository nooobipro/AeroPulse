import { Alert, AppShell, Badge, Burger, Button, Container, Group, Menu, Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconLogout, IconUser } from '@tabler/icons-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useHighlights, useLogout, useMe } from '../api/hooks';
import { COLORS } from '../theme';
import { ROLE_LABEL, ROLE_RANK } from '../utils/format';

const LINKS = [
  { to: '/dashboard', label: 'Панель', role: 'user' },
  { to: '/methods', label: 'Методы анализа', role: 'analyst' },
  { to: '/admin', label: 'Администрирование', role: 'admin' },
];

function Logo() {
  return (
    <Group gap={10} wrap="nowrap">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden>
        <rect width="64" height="64" rx="10" fill="#17324F" />
        <path d="M12 40h40v4H12zM16 22h6v14h-6zM27 16h6v20h-6zM38 26h6v10h-6z" fill={COLORS.amber} />
      </svg>
      <Text className="page-title" fw={700} size="lg" c="white" style={{ letterSpacing: 0 }}>AeroPulse</Text>
    </Group>
  );
}

export default function Layout() {
  const { data: user } = useMe();
  const { data: hl } = useHighlights();
  const logout = useLogout();
  const navigate = useNavigate();
  const links = LINKS.filter((l) => user && ROLE_RANK[user.role] >= ROLE_RANK[l.role]);

  return (
    <AppShell header={{ height: 56 }} padding={0}>
      <AppShell.Header style={{ background: COLORS.board, borderBottom: `3px solid ${COLORS.amber}` }}>
        <Container size="xl" h="100%">
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group gap="xl" wrap="nowrap">
              <NavLink to="/" style={{ textDecoration: 'none' }} aria-label="На главную"><Logo /></NavLink>
              <Group gap={4} visibleFrom="sm" component="nav">
                {links.map((l) => (
                  <NavLink key={l.to} to={l.to} style={{ textDecoration: 'none' }}>
                    {({ isActive }) => (
                      <Text size="sm" fw={500} px="sm" py={6} c="white" style={{ borderRadius: 3, background: isActive ? '#26466E' : 'transparent' }}>{l.label}</Text>
                    )}
                  </NavLink>
                ))}
              </Group>
            </Group>

            <Group gap="xs" wrap="nowrap">
              {links.length > 0 && (
                <Menu position="bottom-end" width={220}>
                  <Menu.Target>
                    <Burger hiddenFrom="sm" size="sm" color="white" opened={false} aria-label="Разделы" />
                  </Menu.Target>
                  <Menu.Dropdown>
                    {links.map((l) => <Menu.Item key={l.to} onClick={() => navigate(l.to)}>{l.label}</Menu.Item>)}
                  </Menu.Dropdown>
                </Menu>
              )}
              {user ? (
                <Menu position="bottom-end" width={240}>
                  <Menu.Target>
                    <UnstyledButton aria-label="Меню пользователя">
                      <Group gap={6} wrap="nowrap">
                        <IconUser size={18} color="white" />
                        <Text size="sm" c="white" visibleFrom="xs" maw={160} truncate>{user.full_name || user.email}</Text>
                        <IconChevronDown size={14} color="white" />
                      </Group>
                    </UnstyledButton>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Label>
                      <Text size="xs" truncate>{user.email}</Text>
                      <Badge size="xs" color="amber.5" variant="light" mt={4}>{ROLE_LABEL[user.role]}</Badge>
                    </Menu.Label>
                    <Menu.Item leftSection={<IconUser size={16} />} onClick={() => navigate('/profile')}>Профиль</Menu.Item>
                    <Menu.Item leftSection={<IconLogout size={16} />} onClick={() => logout.mutate(undefined, { onSettled: () => navigate('/') })}>Выйти</Menu.Item>
                  </Menu.Dropdown>
                </Menu>
              ) : (
                <Group gap="xs" wrap="nowrap">
                  <Button variant="subtle" c="white" size="xs" onClick={() => navigate('/login')}>Войти</Button>
                  <Button color="amber.5" c={COLORS.ink} size="xs" onClick={() => navigate('/register')}>Регистрация</Button>
                </Group>
              )}
            </Group>
          </Group>
        </Container>
      </AppShell.Header>

      <AppShell.Main>
        {hl?.is_demo && (
          <Alert color="yellow" radius={0} py={6} variant="filled" styles={{ message: { color: COLORS.ink } }}>
            <Container size="xl">
              <Text size="sm" fw={500}>Демонстрационный режим: все значения смоделированы и не описывают реальные рейсы.</Text>
            </Container>
          </Alert>
        )}
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
