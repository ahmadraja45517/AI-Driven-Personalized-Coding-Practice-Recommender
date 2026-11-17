import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

import Login from './pages/Login';
import Register from './pages/Register';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Roadmap from './pages/Roadmap';
import SectionDetail from './pages/SectionDetail'; // <-- ADDED
import Analytics from './pages/Analytics';
import Recommendations from './pages/Recommendations';
import AppLayout from './components/layout/AppLayout';
import Assessment from './pages/Assessment';
import Profile from './pages/Profile';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  
  if (loading) return <div className="min-h-screen flex items-center justify-center text-white bg-slate-900">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.onboarding_completed_at) return <Navigate to="/onboarding" replace />;
  
  return <>{children}</>;
}

function AppRoutes() {
  const { user } = useAuth();
  
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/dashboard" /> : <Register />} />
      
      <Route path="/onboarding" element={
        !user ? <Navigate to="/login" /> : 
        user.onboarding_completed_at ? <Navigate to="/dashboard" /> : <Onboarding />
      } />

      {/* Protected Layout Routes */}
      <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="roadmap" element={<Roadmap />} />
        <Route path="roadmap/:id" element={<SectionDetail />} /> {/* <-- ADDED */}
        <Route path="assessment/:id" element={<Assessment />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="profile" element={<Profile />} /> 
      </Route>
      
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}