import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import useAuthStore from './stores/authStore';

// Layout
import DashboardLayout from './components/layout/DashboardLayout';

// Pages
import Dashboard from './pages/Dashboard';
import Assessments from './pages/Assessments';
import AssessmentDetail from './pages/AssessmentDetail';
import Evidence from './pages/Evidence';
import Controls from './pages/Controls';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

// Protected Route Component
function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  if (!isAuthenticated) {
    // Redirect to landing page if not authenticated
    window.location.href = '/';
    return null;
  }

  return children;
}

function App() {
  const { setUser, getUserFromToken, isAuthenticated } = useAuthStore();

  useEffect(() => {
    // Set user from token on mount
    if (isAuthenticated()) {
      const user = getUserFromToken();
      setUser(user);
    }
  }, [isAuthenticated, getUserFromToken, setUser]);

  return (
    <Routes>
      <Route path="/" element={
        <ProtectedRoute>
          <DashboardLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Dashboard />} />
        <Route path="assessments" element={<Assessments />} />
        <Route path="assessments/:id" element={<AssessmentDetail />} />
        <Route path="evidence" element={<Evidence />} />
        <Route path="controls" element={<Controls />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
