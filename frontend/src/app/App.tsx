import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AdminLoginPage } from '../pages/AdminLoginPage';
import { AdminDashboardPage } from '../pages/AdminDashboardPage';
import { AdminCoursesPage } from '../pages/AdminCoursesPage';
import { AdminBatchesPage } from '../pages/AdminBatchesPage';
import { AdminBatchWorkspacePage } from '../pages/AdminBatchWorkspacePage';
import { AdminPaymentsPage } from '../pages/AdminPaymentsPage';
import { AdminSubmittedPaymentsPage } from '../pages/AdminSubmittedPaymentsPage';
import { AdminPaymentDetailPage } from '../pages/AdminPaymentDetailPage';
import { AdminStatementImportsPage } from '../pages/AdminStatementImportsPage';
import { AdminStatementImportDetailPage } from '../pages/AdminStatementImportDetailPage';
import { AdminReconciliationPage } from '../pages/AdminReconciliationPage';
import { AdminReconciliationRunDetailPage } from '../pages/AdminReconciliationRunDetailPage';
import { PublicRegistrationPage } from '../pages/PublicRegistrationPage';
import { PublicPaymentPage } from '../pages/PublicPaymentPage';
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

  // 3.0 Admin Protected Batch Workspace Route (/upi/admin/batches/:batchPublicId/*)
  const batchWorkspaceMatch = currentPath.match(/^(?:\/upi)?\/admin\/batches\/([a-fA-F0-9-]{36})(?:\/(overview|payments|bank-transactions|reconciliation))?\/?$/);
  if (batchWorkspaceMatch) {
    const batchPublicId = batchWorkspaceMatch[1];
    const tabParam = (batchWorkspaceMatch[2] || 'payments') as 'overview' | 'payments' | 'bank-transactions' | 'reconciliation';
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminBatchWorkspacePage batchPublicId={batchPublicId} onNavigate={navigate} initialTab={tabParam} />
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

  // 3.1 Admin Protected Submitted Payments Shortcut (/upi/admin/payments/submitted)
  if (isPath('/upi/admin/payments/submitted') || isPath('/admin/payments/submitted')) {
    const searchParams = Object.fromEntries(new URLSearchParams(window.location.search));
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminSubmittedPaymentsPage onNavigate={navigate} searchParams={searchParams} />
      </ProtectedRoute>
    );
  }

  // 3.2 Admin Protected Payment Detail Route (/upi/admin/payments/:paymentSessionPublicId)
  const adminPaymentDetailMatch = currentPath.match(/^(?:\/upi)?\/admin\/payments\/([a-fA-F0-9-]{36})\/?$/);
  if (adminPaymentDetailMatch) {
    const paymentSessionPublicId = adminPaymentDetailMatch[1];
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminPaymentDetailPage paymentSessionPublicId={paymentSessionPublicId} onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 3.3 Admin Protected Payments List Route (/upi/admin/payments)
  if (isPath('/upi/admin/payments') || isPath('/admin/payments')) {
    const searchParams = Object.fromEntries(new URLSearchParams(window.location.search));
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminPaymentsPage onNavigate={navigate} searchParams={searchParams} />
      </ProtectedRoute>
    );
  }

  // 3.4 Admin Protected Statement Import Detail Route (/upi/admin/statement-imports/:importPublicId)
  const statementImportDetailMatch = currentPath.match(/^(?:\/upi)?\/admin\/statement-imports\/([a-fA-F0-9-]{36})\/?$/);
  if (statementImportDetailMatch) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminStatementImportDetailPage />
      </ProtectedRoute>
    );
  }

  // 3.5 Admin Protected Statement Imports List Route (/upi/admin/statement-imports)
  if (isPath('/upi/admin/statement-imports') || isPath('/admin/statement-imports')) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminStatementImportsPage onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 3.6 Admin Protected Reconciliation Run Detail Route (/upi/admin/reconciliation/runs/:runPublicId)
  const reconciliationRunDetailMatch = currentPath.match(/^(?:\/upi)?\/admin\/reconciliation\/runs\/([a-fA-F0-9-]{36})\/?$/);
  if (reconciliationRunDetailMatch) {
    const runPublicId = reconciliationRunDetailMatch[1];
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminReconciliationRunDetailPage runPublicId={runPublicId} onNavigate={navigate} />
      </ProtectedRoute>
    );
  }

  // 3.7 Admin Protected Reconciliation Route (/upi/admin/reconciliation)
  if (isPath('/upi/admin/reconciliation') || isPath('/admin/reconciliation')) {
    return (
      <ProtectedRoute onNavigate={navigate}>
        <AdminReconciliationPage onNavigate={navigate} />
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

  // 5. Public Registration Route (/upi/register/:batchPublicId or /register/:batchPublicId)
  const registerMatch = currentPath.match(/^(?:\/upi)?\/register\/([a-fA-F0-9-]{36})\/?$/);
  if (registerMatch) {
    const batchPublicId = registerMatch[1];
    return <PublicRegistrationPage batchPublicId={batchPublicId} onNavigate={navigate} />;
  }

  // 6. Public Payment Checkout Route (/upi/payment/:paymentSessionPublicId or /payment/:paymentSessionPublicId)
  const paymentMatch = currentPath.match(/^(?:\/upi)?\/payment\/([a-fA-F0-9-]{36})\/?$/);
  if (paymentMatch) {
    const paymentSessionPublicId = paymentMatch[1];
    return <PublicPaymentPage paymentSessionPublicId={paymentSessionPublicId} onNavigate={navigate} />;
  }

  // 7. Default Public Home (/upi/ or /)
  return (
    <div className="container">
      <header className="header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div className="badge">
            <ShieldCheck size={14} />
            Phase 9 — Google Pay / UPI Statement Import
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
        <p>Samagra UPI Automation Platform &bull; Phase 9 Statement Import Verified</p>
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
