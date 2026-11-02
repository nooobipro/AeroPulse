import { Alert, Anchor, Button, Center, Container, Paper, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useLogin, useRegister } from '../api/hooks';

function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Container size={440} py={56}>
      <Paper p="xl" shadow="xs">
        <Stack gap="md">
          <Title order={2} className="page-title">{title}</Title>
          {children}
        </Stack>
      </Paper>
    </Container>
  );
}

export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email: email.trim(), password }, { onSuccess: () => navigate(from, { replace: true }) });
  };

  return (
    <AuthShell title="Вход">
      <form onSubmit={submit}>
        <Stack gap="sm">
          {login.error && <Alert color="red" role="alert">{login.error.message}</Alert>}
          <TextInput label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.currentTarget.value)} data-autofocus />
          <PasswordInput label="Пароль" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.currentTarget.value)} />
          <Button type="submit" loading={login.isPending} color="amber.5" c="#0E2238" fullWidth mt="xs">Войти</Button>
        </Stack>
      </form>
      <Center><Text size="sm">Нет аккаунта? <Anchor component={Link} to="/register">Зарегистрироваться</Anchor></Text></Center>
    </AuthShell>
  );
}

export function RegisterPage() {
  const register = useRegister();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', repeat: '' });
  const [localError, setLocalError] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.currentTarget.value });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (form.password !== form.repeat) { setLocalError('Пароли не совпадают'); return; }
    register.mutate({ email: form.email.trim(), password: form.password, full_name: form.full_name.trim() }, { onSuccess: () => navigate('/dashboard', { replace: true }) });
  };

  return (
    <AuthShell title="Регистрация">
      <form onSubmit={submit}>
        <Stack gap="sm">
          {(localError || register.error) && <Alert color="red" role="alert">{localError ?? register.error?.message}</Alert>}
          <TextInput label="Имя" description="Необязательно" autoComplete="name" maxLength={100} value={form.full_name} onChange={set('full_name')} />
          <TextInput label="Email" type="email" autoComplete="email" required value={form.email} onChange={set('email')} />
          <PasswordInput label="Пароль" description="Не менее 8 символов, буквы и цифры" autoComplete="new-password" required value={form.password} onChange={set('password')} />
          <PasswordInput label="Повторите пароль" autoComplete="new-password" required value={form.repeat} onChange={set('repeat')} />
          <Button type="submit" loading={register.isPending} color="amber.5" c="#0E2238" fullWidth mt="xs">Создать аккаунт</Button>
        </Stack>
      </form>
      <Center><Text size="sm">Уже есть аккаунт? <Anchor component={Link} to="/login">Войти</Anchor></Text></Center>
    </AuthShell>
  );
}
