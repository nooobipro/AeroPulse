import { Button, Center, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <Center py={80}>
      <Stack align="center" gap="xs">
        <Title order={1} className="page-title" fz={64}>404</Title>
        <Text c="dimmed">Такой страницы нет.</Text>
        <Button component={Link} to="/" variant="default" mt="sm">На главную</Button>
      </Stack>
    </Center>
  );
}
