import { Button, Center, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { useMe } from '../api/hooks';
import { PageLoader } from '../components/common';
import { ROLE_RANK } from '../utils/format';

export function Forbidden() {
  return (
    <Center py={80}>
      <Stack align="center" gap="xs">
        <Title order={2} className="page-title">Недостаточно прав</Title>
        <Text c="dimmed">У вашей роли нет доступа к этому разделу.</Text>
        <Button component={Link} to="/dashboard" variant="default" mt="sm">Вернуться на панель</Button>
      </Stack>
    </Center>
  );
}

/** Доступ только для вошедших пользователей с нужной ролью. Окончательно права всегда проверяет сервер. */
export function RequireAuth({ role = 'user', children }: { role?: 'user' | 'analyst' | 'admin'; children: ReactNode }) {
  const { data: user, isLoading } = useMe();
  const location = useLocation();
  if (isLoading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (ROLE_RANK[user.role] < ROLE_RANK[role]) return <Forbidden />;
  return <>{children}</>;
}

/** Страницы входа и регистрации не нужны уже вошедшему пользователю. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useMe();
  if (isLoading) return <PageLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
