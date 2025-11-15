import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Assessments } from './pages/Assessments';
import { Controls } from './pages/Controls';
import { Evidence } from './pages/Evidence';
import { Reports } from './pages/Reports';
import { BulkOperations } from './pages/BulkOperations';
import { Settings } from './pages/Settings';
import { Integrations } from './pages/Integrations';
import { DocumentManagement } from './pages/DocumentManagement';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/assessments" element={<Assessments />} />
            <Route path="/assessments/:id" element={<Dashboard />} />
            <Route path="/controls" element={<Controls />} />
            <Route path="/controls/:assessmentId" element={<Controls />} />
            <Route path="/evidence" element={<Evidence />} />
            <Route path="/evidence/:assessmentId" element={<Evidence />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/bulk" element={<BulkOperations />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/documents" element={<DocumentManagement />} />
            <Route path="/analytics" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          {/* 404 Route */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
