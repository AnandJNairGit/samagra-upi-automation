/**
 * Admin Authentication Verification Dashboard
 */

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getAdminHealthApi } from '../services/apiClient';
import { AdminHealthResponse } from '../types/auth';
import {
  ShieldCheck,
  UserCheck,
  LogOut,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from 'lucide-react';

interface AdminDashboardPageProps {
  onNavigate: (path: string) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onNavigate }) => {
  const { admin, logout, logoutAll } = useAuth();
  const [healthData, setHealthData] = useState<AdminHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState<boolean>(false);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await getAdminHealthApi();
      setHealthData(data);
    } catch (err: any) {
      setHealthError(err.message || 'Authorization check failed');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      onNavigate('/upi/admin/login');
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleLogoutAll = async () => {
    if (!window.confirm('Are you sure you want to revoke all active sessions across all devices?')) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await logoutAll();
      onNavigate('/upi/admin/login');
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="badge success-badge">
          <ShieldCheck size={14} />
          Phase 3 — Authenticated & Authorized
        </div>
        <h1 className="title">Admin Control Console</h1>
        <p className="subtitle">
          Secure administrator identity and authorization foundation.
        </p>
      </header>

      <div className="grid-2">
        {/* Administrator Profile Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <UserCheck size={20} color="#818cf8" />
              Active Administrator Profile
            </h2>
          </div>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Full Name</td>
                <td className="meta-val font-semibold">{admin?.full_name || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Email Address</td>
                <td className="meta-val">{admin?.email || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Account Status</td>
                <td className="meta-val">
                  <span className="status-pill active-pill">
                    <CheckCircle2 size={12} /> Active
                  </span>
                </td>
              </tr>
              <tr>
                <td className="meta-key">Public UUID</td>
                <td className="meta-val monospace">{admin?.public_id || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Token Storage</td>
                <td className="meta-val">
                  <span className="secure-tag">React Memory (Zero localStorage)</span>
                </td>
              </tr>
            </tbody>
          </table>

          <div className="action-row" style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
            <button
              id="admin-logout-btn"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="btn btn-outline"
            >
              <LogOut size={16} />
              {isLoggingOut ? 'Logging out...' : 'Sign Out'}
            </button>
            <button
              id="admin-logout-all-btn"
              onClick={handleLogoutAll}
              disabled={isLoggingOut}
              className="btn btn-danger-outline"
            >
              <AlertTriangle size={16} />
              Revoke All Sessions
            </button>
          </div>
        </div>

        {/* Authorization Middleware Live Check */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className="card-title">
              <Radio size={20} color="#38bdf8" />
              Protected API Authorization
            </h2>
            <button
              onClick={fetchHealth}
              disabled={healthLoading}
              className="icon-btn"
              title="Re-verify Authorization"
            >
              <RefreshCw size={14} className={healthLoading ? 'spinner' : ''} />
            </button>
          </div>

          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1rem' }}>
            Validates live authorization middleware on <code>/v1/admin/health</code> using your in-memory Bearer token.
          </p>

          {healthLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              <Loader2 size={24} className="spinner" color="#38bdf8" />
              <p style={{ color: '#94a3b8', fontSize: '0.8125rem', marginTop: '0.5rem' }}>Testing endpoint authorization...</p>
            </div>
          ) : healthError ? (
            <div className="error-banner">
              <AlertTriangle size={16} color="#ef4444" />
              <span>Authorization Failed: {healthError}</span>
            </div>
          ) : (
            <div className="verification-box">
              <div className="verification-item">
                <span className="verify-label">Endpoint Status:</span>
                <span className="verify-value success">{healthData?.status.toUpperCase()}</span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Authorization Guard:</span>
                <span className="verify-value success">
                  <CheckCircle2 size={14} /> Passed (require_admin)
                </span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Verified Email:</span>
                <span className="verify-value">{healthData?.admin_email}</span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Verified Public ID:</span>
                <span className="verify-value monospace">{healthData?.admin_public_id}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
