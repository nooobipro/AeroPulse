import { Badge, Container, Group, Paper, PasswordInput, SimpleGrid, Stack, Text, TextInput, Title, Button, Alert } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { FormEvent, useEffect, useState } from 'react';
import { useChangePassword, useMe, useUpdateProfile } from '../api/hooks';
import { ROLE_LABEL, fmtDateTime } from '../utils/format';

export default function Profile() {
  const { data: me } = useMe();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const [name, setName] = useState('');
  const [pw, setPw] = useState({ current: '', next: '', repeat: '' });
  const [pwError, setPwError] = useState<string | null>(null);
  useEffect(() => setName(me?.full_name ?? ''), [me?.full_name]);
  if (!me) return null;

  const saveName = (e: FormEvent) => {
    e.preventDefault();
    updateProfile.mutate(name, { onSuccess: () => notifications.show({ color: 'teal', message: 'Профиль обновлён' }) });
  };
  const savePassword = (e: FormEvent) => {
    e.preventDefault();
    setPwError(null);
    if (pw.next !== pw.repeat) { setPwError('Новые пароли не совпадают'); return; }
    changePassword.mutate({ current_password: pw.current, new_password: pw.next }, {
      onSuccess: () => { setPw({ current: '', next: '', repeat: '' }); notifications.show({ color: 'teal', message: 'Пароль изменён. На других устройствах потребуется войти заново.' }); },
    });
  };

  return (
    <Container size="md" py="lg">
      <Stack gap="md">
        <Title order={2} className="page-title">Профиль</Title>
        <Paper p="md">
          <Group gap="xl" wrap="wrap">
            <div><Text size="xs" c="dimmed">Email</Text><Text fw={500}>{me.email}</Text></div>
            <div><Text size="xs" c="dimmed">Роль</Text><Badge color="amber.5" variant="light">{ROLE_LABEL[me.role]}</Badge></div>
            <div><Text size="xs" c="dimmed">Зарегистрирован</Text><Text>{fmtDateTime(me.created_at)}</Text></div>
            <div><Text size="xs" c="dimmed">Последний вход</Text><Text>{fmtDateTime(me.last_login_at)}</Text></div>
          </Group>
          <Text size="xs" c="dimmed" mt="sm">Роль меняет только администратор.</Text>
        </Paper>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
          <Paper p="md" component="form" onSubmit={saveName}>
            <Stack gap="sm">
              <Title order={4} className="page-title">Имя</Title>
              {updateProfile.error && <Alert color="red">{updateProfile.error.message}</Alert>}
              <TextInput label="Отображаемое имя" maxLength={100} value={name} onChange={(e) => setName(e.currentTarget.value)} />
              <Button type="submit" loading={updateProfile.isPending} disabled={name.trim() === me.full_name}>Сохранить</Button>
            </Stack>
          </Paper>
          <Paper p="md" component="form" onSubmit={savePassword}>
            <Stack gap="sm">
              <Title order={4} className="page-title">Смена пароля</Title>
              {(pwError || changePassword.error) && <Alert color="red">{pwError ?? changePassword.error?.message}</Alert>}
              <PasswordInput label="Текущий пароль" autoComplete="current-password" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.currentTarget.value })} />
              <PasswordInput label="Новый пароль" description="Не менее 8 символов, буквы и цифры" autoComplete="new-password" required value={pw.next} onChange={(e) => setPw({ ...pw, next: e.currentTarget.value })} />
              <PasswordInput label="Повторите новый пароль" autoComplete="new-password" required value={pw.repeat} onChange={(e) => setPw({ ...pw, repeat: e.currentTarget.value })} />
              <Button type="submit" loading={changePassword.isPending}>Изменить пароль</Button>
            </Stack>
          </Paper>
        </SimpleGrid>
      </Stack>
    </Container>
  );
}
