import React, { useEffect, useState } from 'react';
import AdminNav from '../components/AdminNav';
import { reconciliationApi } from '../services/reconciliationApi';
import { statementImportApi } from '../services/statementImportApi';
import { ReconciliationRunResponse } from '../types/reconciliation';
import { StatementImportListItem } from '../types/statementImport';
import {
  GitCompare,
  Play,
  RefreshCw,
  Loader2,
  AlertCircle,
  FileText,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  ArrowRight,
} from 'lucide-react';

interface AdminReconciliationPageProps {
  onNavigate?: (path: string) => void;
}

export const AdminReconciliationPage: React.FC<AdminReconciliationPageProps> = ({ onNavigate }) => {
  const navigateTo = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  // State
  const [statementImports, setStatementImports] = useState<StatementImportListItem[]>([]);
  const [runs, setRuns] = useState<ReconciliationRunResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch data
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRunsCount, setTotalRunsCount] = useState(0);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch imports ready for reconciliation
      const importsRes = await statementImportApi.getStatementImports(1, 10);
      setStatementImports(importsRes.items);

      // Fetch runs history
      const runsRes = await reconciliationApi.getReconciliationRuns(undefined, undefined, page, 20);
      setRuns(runsRes.items);
      setTotalRunsCount(runsRes.total);
      setTotalPages(runsRes.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reconciliation data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  const handleStartReconciliation = () => {
    // New batch-scoped reconciliation workflow: navigate user to Batches Workspace
    navigateTo('/upi/admin/batches');
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="reconciliation" onNavigate={navigateTo} />

      <header className="page-header">
        <div>
          <div className="badge">
            <GitCompare size={14} />
            Deterministic Reconciliation Engine
          </div>
          <h1 className="page-title">Payment Reconciliation</h1>
          <p className="page-subtitle">
            Compare imported bank statement transactions against system payment records using payment Reference Codes.
          </p>
        </div>

        <div className="page-actions">
          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="btn btn-outline"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} color="#ef4444" />
          <span>{error}</span>
        </div>
      )}

      {/* Section 1: Available Statement Imports Ready to Reconcile */}
      <div className="card" style={{ marginBottom: '24px', padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
              Statement Files Available for Reconciliation
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
              Select a completed bank statement import to evaluate transactions against payment sessions.
            </p>
          </div>
        </div>

        {statementImports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
            <FileSpreadsheet size={36} color="#64748b" style={{ margin: '0 auto 10px' }} />
            <p style={{ color: '#e2e8f0', fontSize: '0.95rem', fontWeight: 600 }}>No statement files uploaded yet.</p>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
              Upload a Google Pay or Bank statement first in the Statement Imports tab.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Format</th>
                  <th style={{ textAlign: 'right' }}>Total Txns</th>
                  <th style={{ textAlign: 'right' }}>New Entries</th>
                  <th>Uploaded Date</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {statementImports.map((imp) => (
                  <tr key={imp.public_id}>
                    <td>
                      <span className="font-semibold" style={{ color: '#f8fafc' }}>{imp.filename}</span>
                    </td>
                    <td>
                      <span className="count-badge uppercase" style={{ fontWeight: 600 }}>
                        {imp.file_type}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{imp.total_rows}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }} className="amount-highlight font-semibold">
                      +{imp.new_transactions}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {new Date(imp.created_at).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={handleStartReconciliation}
                        className="btn btn-primary btn-sm"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' }}
                      >
                        <Play size={14} />
                        <span>Reconcile in Workspace</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 2: Reconciliation Run History */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
              Reconciliation Run History ({totalRunsCount})
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
              Audit trail of previous automated reconciliation passes and detailed outcome breakdown.
            </p>
          </div>
        </div>

        {loading && runs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0' }}>
            <Loader2 size={32} className="spinner" color="#818cf8" />
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Loading reconciliation history...</p>
          </div>
        ) : runs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <GitCompare size={40} color="#64748b" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 600 }}>No reconciliation runs executed yet.</p>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Click "Run Reconciliation" on any statement file above to start your first payment matching run.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Statement File</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Total Txns</th>
                  <th style={{ textAlign: 'right' }}>Matched</th>
                  <th style={{ textAlign: 'right' }}>Amt Mismatch</th>
                  <th style={{ textAlign: 'right' }}>UTR Mismatch</th>
                  <th style={{ textAlign: 'right' }}>Unknown Ref</th>
                  <th>Execution Date</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.public_id}>
                    <td>
                      <span className="font-semibold" style={{ color: '#f8fafc' }}>{run.filename}</span>
                    </td>
                    <td>
                      {run.status === 'COMPLETED' ? (
                        <span className="status-pill active-pill">Completed</span>
                      ) : run.status === 'RUNNING' ? (
                        <span className="status-pill pending-pill">Running</span>
                      ) : (
                        <span className="status-pill archived-pill">{run.status}</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{run.total_transactions}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: '#34d399', fontWeight: 600 }}>
                      {run.matched_count}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: run.amount_mismatch_count > 0 ? '#ef4444' : '#94a3b8' }}>
                      {run.amount_mismatch_count}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: run.utr_mismatch_count > 0 ? '#f59e0b' : '#94a3b8' }}>
                      {run.utr_mismatch_count}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: run.unknown_reference_count > 0 ? '#60a5fa' : '#94a3b8' }}>
                      {run.unknown_reference_count}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => navigateTo(`/upi/admin/reconciliation/runs/${run.public_id}`)}
                        className="btn-action"
                      >
                        <FileText size={12} />
                        <span>View Results</span>
                        <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.15)' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Page {page} of {totalPages} ({totalRunsCount} total runs)
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn btn-sm btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <ChevronLeft size={14} />
                <span>Previous</span>
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="btn btn-sm btn-outline"
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <span>Next</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminReconciliationPage;
