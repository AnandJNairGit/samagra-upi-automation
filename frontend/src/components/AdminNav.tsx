import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  BookOpen,
  Layers,
  CreditCard,
  CheckSquare,
  FileSpreadsheet,
  LogOut,
  User,
  ShieldCheck,
} from 'lucide-react';

interface AdminNavProps {
  activeTab?: 'dashboard' | 'courses' | 'batches' | 'payments' | 'submitted' | 'statement-imports';
  onNavigate?: (path: string) => void;
}

export const AdminNav: React.FC<AdminNavProps> = ({ activeTab, onNavigate }) => {
  const { admin, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const navigateTo = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      navigateTo('/upi/admin/login');
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <nav className="admin-nav-bar">
      <div className="admin-nav-left">
        <div
          className="admin-brand"
          onClick={() => navigateTo('/upi/admin')}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <ShieldCheck size={20} color="#818cf8" />
          <span className="brand-text">Admin Console</span>
        </div>

        <div className="admin-nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin')}
          >
            <LayoutDashboard size={16} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'courses' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin/courses')}
          >
            <BookOpen size={16} />
            <span>Courses</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'batches' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin/batches')}
          >
            <Layers size={16} />
            <span>Batches</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'payments' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin/payments')}
          >
            <CreditCard size={16} />
            <span>Payments</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'submitted' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin/payments/submitted')}
          >
            <CheckSquare size={16} />
            <span>Submitted</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'statement-imports' ? 'active' : ''}`}
            onClick={() => navigateTo('/upi/admin/statement-imports')}
          >
            <FileSpreadsheet size={16} />
            <span>Statement Imports</span>
          </button>
        </div>
      </div>

      <div className="admin-nav-right">
        {admin && (
          <div className="admin-user-pill" title={admin.email}>
            <User size={14} />
            <span>{admin.full_name || admin.email}</span>
          </div>
        )}
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="btn btn-sm btn-outline"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <LogOut size={14} />
          <span>{isLoggingOut ? 'Signing out...' : 'Sign Out'}</span>
        </button>
      </div>
    </nav>
  );
};

export default AdminNav;
