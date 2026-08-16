import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AdminLoginPage } from '../pages/AdminLoginPage';
import { AdminDashboardPage } from '../pages/AdminDashboardPage';
import { AdminCoursesPage } from '../pages/AdminCoursesPage';
import { AdminBatchesPage } from '../pages/AdminBatchesPage';
import { HealthStatus } from '../components/HealthStatus';
import { ShieldCheck, Layers, LogIn, LayoutDashboard } from 'lucide-react';

const AppContent: React.FC = () => {
  const [currentPath, setCurrentPath] = useState<string>(window.location.pathname);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(window.location.pathname);
  };

  // Route matching helper
  const isPath = (target: string) => {
    const normalized = currentPath.endsWith('/') && currentPath.length > 1 ? currentPath.slice(0, -1) : currentPath;
    const targetNorm = target.endsWith('/') && target.length > 1 ? target.slice(0, -1) : target;
    return normalized === targetNorm || normalized === `${targetNorm}/`;
  };

  // 1. Admin Login Route (/upi/admin/login or /admin/login)
  if (isPath('/upi/admin/login') || isPath('/admin/login')) {
    return <AdminLoginPage onNavigate={navigate} />;
  }

  // 2. Admin Protected Courses Route (/upi/admin/courses or /admin/courses)
  if (isPath('/upi/admin/courses') || isPath('/admin/courses')) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminCoursesPage onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 3. Admin Protected Batches Route (/upi/admin/batches or /admin/batches)
  if (isPath('/upi/admin/batches') || isPath('/admin/batches')) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminBatchesPage onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 4. Admin Protected Dashboard Root (/upi/admin or /admin)
  if (isPath('/upi/admin') || isPath('/admin')) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminDashboardPage onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 5. Default Public Home (/upi/ or /)
  return (
    <div className="container">
      <header className="header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div className="badge">
            <ShieldCheck size={14} />
            Phase 4 — Course & Batch Management
          </div>
          <div>
            {isAuthenticated ? (
              <button
                onClick={() => navigate('/upi/admin')}
                className="btn btn-sm btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}
              >
                <LayoutDashboard size={14} />
                Admin Console
              </button>
            ) : (
              <button
                onClick={() => navigate('/upi/admin/login')}
                className="btn btn-sm btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}
              >
                <LogIn size={14} />
                Admin Sign In
              </button>
            )}
          </div>
        </div>
        <h1 className="title">Samagra UPI Automation</h1>
        <p className="subtitle">
          Modular monolith stack: Vite + React, FastAPI, PostgreSQL, and Host Caddy.
        </p>
      </header>

      <main>
        <HealthStatus />

        <div className="card">
          <h2 className="card-title">
            <Layers size={20} color="#a78bfa" />
            Active Service Topologies & Namespaces
          </h2>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Host Reverse Proxy</td>
                <td className="meta-val">Host Caddy (Ports 80 / 443)</td>
              </tr>
              <tr>
                <td className="meta-key">Public URL Routes</td>
                <td className="meta-val">/upi/* (Frontend), /upi-api/* (Backend)</td>
              </tr>
              <tr>
                <td className="meta-key">Admin Portal Route</td>
                <td className="meta-val">
                  <a
                    href="/upi/admin/login"
                    onClick={(e) => {
                      e.preventDefault();
                      navigate('/upi/admin/login');
                    }}
                    style={{ color: '#818cf8', textDecoration: 'underline' }}
                  >
                    /upi/admin/login
                  </a>
                </td>
              </tr>
              <tr>
                <td className="meta-key">Frontend Host Port</td>
                <td className="meta-val">127.0.0.1:8080 (Prod) / 127.0.0.1:5173 (Dev)</td>
              </tr>
              <tr>
                <td className="meta-key">Backend Host Port</td>
                <td className="meta-val">127.0.0.1:8001 (FastAPI Container)</td>
              </tr>
              <tr>
                <td className="meta-key">PostgreSQL Storage</td>
                <td className="meta-val">./docker/postgres/data (Host Bind Mount)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>

      <footer className="footer">
        <p>Samagra UPI Automation Platform &bull; Phase 4 Verified</p>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};
