import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';
import Login from './pages/Login';
import Chat from './pages/Chat';
import AgentDashboard from './pages/AgentDashboard';
import ManagerPortal from './pages/ManagerPortal';
import AdminPanel from './pages/AdminPanel';

const queryClient = new QueryClient();

function ProtectedRoute({ children, roles }) {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/login" replace />;
  return children;
}

function RoleRedirect() {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;
  const routes = { customer: '/chat', agent: '/agent', manager: '/manager', admin: '/admin' };
  return <Navigate to={routes[user.role] || '/chat'} replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RoleRedirect />} />
          <Route path="/chat" element={
            <ProtectedRoute roles={['customer']}>
              <Chat />
            </ProtectedRoute>
          } />
          <Route path="/agent" element={
            <ProtectedRoute roles={['agent', 'admin']}>
              <AgentDashboard />
            </ProtectedRoute>
          } />
          <Route path="/manager" element={
            <ProtectedRoute roles={['manager', 'admin']}>
              <ManagerPortal />
            </ProtectedRoute>
          } />
          <Route path="/admin" element={
            <ProtectedRoute roles={['admin']}>
              <AdminPanel />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.875rem',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
        }}
      />
    </QueryClientProvider>
  );
}
