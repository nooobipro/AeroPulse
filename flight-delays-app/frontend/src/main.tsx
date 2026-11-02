import '@fontsource/fira-sans/cyrillic-400.css';
import '@fontsource/fira-sans/cyrillic-500.css';
import '@fontsource/fira-sans/cyrillic-600.css';
import '@fontsource/fira-sans/latin-400.css';
import '@fontsource/fira-sans/latin-500.css';
import '@fontsource/fira-sans/latin-600.css';
import '@fontsource/fira-sans-condensed/cyrillic-600.css';
import '@fontsource/fira-sans-condensed/cyrillic-700.css';
import '@fontsource/fira-sans-condensed/latin-600.css';
import '@fontsource/fira-sans-condensed/latin-700.css';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import './index.css';

import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ApiError } from './api/client';
import App from './App';
import { theme } from './theme';

const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      // Сессия истекла или пользователя заблокировали — возвращаем на страницу входа
      if (error instanceof ApiError && error.status === 401 && query.queryKey[0] !== 'me') {
        queryClient.setQueryData(['me'], null);
      }
    },
  }),
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
