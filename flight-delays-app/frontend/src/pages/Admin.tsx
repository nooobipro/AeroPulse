import { Container, Stack, Tabs, Text, Title } from '@mantine/core';
import { useSearchParams } from 'react-router-dom';
import AuditTab from './admin/AuditTab';
import DataTab from './admin/DataTab';
import DictionariesTab from './admin/DictionariesTab';
import UsersTab from './admin/UsersTab';

const TABS = ['users', 'audit', 'dictionaries', 'data'];

export default function Admin() {
  const [sp, setSp] = useSearchParams();
  const requested = sp.get('tab') ?? 'users';
  const tab = TABS.includes(requested) ? requested : 'users';
  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <div>
          <Title order={2} className="page-title">Администрирование</Title>
          <Text size="sm" c="dimmed">Пользователи и роли, журнал действий, справочники и сведения о загруженных данных.</Text>
        </div>
        <Tabs value={tab} keepMounted={false} color="amber.5" onChange={(v) => setSp({ tab: v ?? 'users' }, { replace: true })}>
          <Tabs.List style={{ flexWrap: 'nowrap', overflowX: 'auto' }}>
            <Tabs.Tab value="users">Пользователи</Tabs.Tab>
            <Tabs.Tab value="audit">Журнал действий</Tabs.Tab>
            <Tabs.Tab value="dictionaries">Справочники</Tabs.Tab>
            <Tabs.Tab value="data">Данные</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="users" pt="md"><UsersTab /></Tabs.Panel>
          <Tabs.Panel value="audit" pt="md"><AuditTab /></Tabs.Panel>
          <Tabs.Panel value="dictionaries" pt="md"><DictionariesTab /></Tabs.Panel>
          <Tabs.Panel value="data" pt="md"><DataTab /></Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
