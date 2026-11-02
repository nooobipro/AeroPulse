import { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { GuestOnly, RequireAuth } from './auth/guards';
import { PageLoader } from './components/common';
import Layout from './components/Layout';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import Dashboard from './pages/Dashboard';
import Landing from './pages/Landing';
import NotFound from './pages/NotFound';
import Profile from './pages/Profile';

// Разделы для аналитика и администратора грузятся по требованию — основной бандл остаётся лёгким
const Methods = lazy(() => import('./pages/Methods'));
const Admin = lazy(() => import('./pages/Admin'));

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="login" element={<GuestOnly><LoginPage /></GuestOnly>} />
          <Route path="register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
          <Route path="dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="methods" element={<RequireAuth role="analyst"><Methods /></RequireAuth>} />
          <Route path="admin" element={<RequireAuth role="admin"><Admin /></RequireAuth>} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
