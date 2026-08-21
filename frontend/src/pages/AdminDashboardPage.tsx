import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { useAuth } from '../context/AuthContext';
import { fetchAdminDashboardSummary } from '../services/adminPaymentApi';
import { AdminDashboardSummary } from '../types/adminPayment';
import {
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  CreditCard,
  CheckSquare,
  Clock,
  XCircle,
  IndianRupee,
  Layers,
  BookOpen,
  ArrowRight,
} from 'lucide-react';

interface AdminDashboardPageProps {
  onNavigate: (path: string) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onNavigate }) => {
  const { admin } = useAuth();

  // Summary Metrics State
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const loadSummaryMetrics = async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await fetchAdminDashboardSummary();
      setSummary(data);
    } catch (err: any) {
      setSummaryError(err.message || 'Unable to load payment summary metrics');
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => {
    loadSummaryMetrics();
  }, []);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="dashboard" onNavigate={onNavigate} />

      <header className="page-header">
        <div className="page-title-bar">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Live overview of participant registrations, payment settlements, and cohort performance.
          </p>
        </div>
        <button
          onClick={loadSummaryMetrics}
          disabled={summaryLoading}
          className="btn btn-sm btn-outline"
          title="Refresh Summary Metrics"
        >
          <RefreshCw size={14} className={summaryLoading ? 'spinner' : ''} />
          Refresh
        </button>
      </header>

      {/* Summary Metrics Grid */}
      <div style={{ marginBottom: '28px' }}>
        {summaryError ? (
          <div className="error-banner">
            <AlertTriangle size={16} />
            <span>{summaryError}</span>
          </div>
        ) : summaryLoading ? (
          <div className="grid-3">
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div key={idx} className="skeleton skeleton-metric" />
            ))}
          </div>
        ) : summary ? (
          <div className="grid-3">
            {/* Total Registrations */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Total Registrations</span>
                  <div className="metric-value">{summary.total_registrations}</div>
                  <span className="metric-sub">All payment sessions</span>
                </div>
                <div className="metric-icon metric-icon-accent">
                  <CreditCard size={20} />
                </div>
              </div>
            </div>

            {/* Pending Payments */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments?status=PENDING')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Pending Payments</span>
                  <div className="metric-value metric-value-warning">{summary.pending_payments}</div>
                  <span className="metric-sub">Awaiting participant transfer</span>
                </div>
                <div className="metric-icon metric-icon-warning">
                  <Clock size={20} />
                </div>
              </div>
            </div>

            {/* Submitted Payments */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments/submitted')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Submitted Payments</span>
                  <div className="metric-value metric-value-success">{summary.submitted_payments}</div>
                  <span className="metric-sub">UTR submitted, pending review</span>
                </div>
                <div className="metric-icon metric-icon-success">
                  <CheckSquare size={20} />
                </div>
              </div>
            </div>

            {/* Approved Payments */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments?status=APPROVED')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Approved Payments</span>
                  <div className="metric-value metric-value-success">{summary.approved_payments}</div>
                  <span className="metric-sub">Reconciled & confirmed</span>
                </div>
                <div className="metric-icon metric-icon-success">
                  <CheckCircle2 size={20} />
                </div>
              </div>
            </div>

            {/* Rejected Payments */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments?status=REJECTED')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Rejected Payments</span>
                  <div className="metric-value metric-value-danger">{summary.rejected_payments}</div>
                  <span className="metric-sub">Invalid or rejected claims</span>
                </div>
                <div className="metric-icon metric-icon-danger">
                  <XCircle size={20} />
                </div>
              </div>
            </div>

            {/* Total Revenue Collected */}
            <div
              className="metric-card"
              onClick={() => onNavigate('/upi/admin/payments?status=APPROVED')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Total Revenue</span>
                  <div className="metric-value metric-value-purple">{formatINR(summary.total_amount_collected_inr)}</div>
                  <span className="metric-sub">Approved sessions only</span>
                </div>
                <div className="metric-icon metric-icon-purple">
                  <IndianRupee size={20} />
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Main Grid: Management Portals & Admin Profile */}
      <div className="grid-2">
        {/* Quick Management Navigation */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Layers size={18} color="var(--accent-light)" />
              Catalog & Batch Management
            </h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '16px', lineHeight: 1.5 }}>
            Configure training courses, manage batch cohorts, monitor capacity, and share enrollment links with prospective participants.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              onClick={() => onNavigate('/upi/admin/courses')}
              className="btn btn-outline"
              style={{ justifyContent: 'space-between', padding: '12px 16px' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BookOpen size={16} color="var(--accent-light)" />
                Manage Courses Catalog
              </span>
              <ArrowRight size={15} color="var(--text-muted)" />
            </button>

            <button
              onClick={() => onNavigate('/upi/admin/batches')}
              className="btn btn-outline"
              style={{ justifyContent: 'space-between', padding: '12px 16px' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={16} color="var(--accent-light)" />
                Manage Batch Cohorts & Workspaces
              </span>
              <ArrowRight size={15} color="var(--text-muted)" />
            </button>
          </div>
        </div>

        {/* Administrator Profile Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <UserCheck size={18} color="var(--accent-light)" />
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
                  <span className={`status-badge ${admin?.is_active !== false ? 'status-badge-active' : 'status-badge-inactive'}`}>
                    <CheckCircle2 size={12} /> {admin?.is_active !== false ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
