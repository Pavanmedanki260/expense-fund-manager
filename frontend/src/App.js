import React from 'react';
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AuthCallback from './pages/AuthCallback';
import Login from './pages/Login';
import GroupList from './pages/GroupList';
import GroupDashboard from './pages/GroupDashboard';
import FundList from './pages/FundList';
import UtilizationList from './pages/UtilizationList';
import Reports from './pages/Reports';
import GroupMembers from './pages/GroupMembers';
import AcceptInvite from './pages/AcceptInvite';
import GroupLayout from './components/GroupLayout';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/invite/:inviteId" element={<AcceptInvite />} />
      <Route path="/groups" element={<ProtectedRoute><GroupList /></ProtectedRoute>} />
      <Route path="/groups/:groupId/dashboard" element={<ProtectedRoute><GroupLayout><GroupDashboard /></GroupLayout></ProtectedRoute>} />
      <Route path="/groups/:groupId/funds" element={<ProtectedRoute><GroupLayout><FundList /></GroupLayout></ProtectedRoute>} />
      <Route path="/groups/:groupId/utilizations" element={<ProtectedRoute><GroupLayout><UtilizationList /></GroupLayout></ProtectedRoute>} />
      <Route path="/groups/:groupId/reports" element={<ProtectedRoute><GroupLayout><Reports /></GroupLayout></ProtectedRoute>} />
      <Route path="/groups/:groupId/members" element={<ProtectedRoute><GroupLayout><GroupMembers /></GroupLayout></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/groups" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: { background: 'var(--surface)', color: 'var(--text-body)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '14px' }
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
