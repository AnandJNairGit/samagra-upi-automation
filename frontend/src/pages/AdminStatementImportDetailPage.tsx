import React, { useEffect, useState } from 'react';
import AdminNav from '../components/AdminNav';
import { statementImportApi } from '../services/statementImportApi';
import {
  BankTransactionItem,
  StatementImportDetail,
} from '../types/statementImport';
import {
  ArrowLeft,
  FileSpreadsheet,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Database,
  Hash,
  Trash2,
  X,
} from 'lucide-react';

interface AdminStatementImportDetailPageProps {
  importPublicId?: string;
  onNavigate?: (path: string) => void;
}

export const AdminStatementImportDetailPage: React.FC<AdminStatementImportDetailPageProps> = ({
  importPublicId: propImportPublicId,
  onNavigate,
}) => {
  const effectiveImportPublicId =
    propImportPublicId ||
    window.location.pathname.match(/^(?:\/upi)?\/admin\/statement-imports\/([a-fA-F0-9-]{36})\/?$/)?.[1];

  const navigateTo = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  const [detail, setDetail] = useState<StatementImportDetail | null>(null);
  const [transactions, setTransactions] = useState<BankTransactionItem[]>([]);
  const [totalTxns, setTotalTxns] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [loading, setLoading] = useState(true);
  const [txnsLoading, setTxnsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!effectiveImportPublicId) return;

    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await statementImportApi.getStatementImportDetail(effectiveImportPublicId);
        setDetail(data);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch statement import details.');
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [effectiveImportPublicId]);

  const fetchTransactions = async (targetPage: number = 1) => {
    if (!effectiveImportPublicId) return;
    setTxnsLoading(true);
    try {
      const res = await statementImportApi.getImportTransactions(effectiveImportPublicId, targetPage, 20);
      setTransactions(res.items);
      setTotalTxns(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      console.error('Failed to fetch import transactions:', err);
    } finally {
      setTxnsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions(page);
  }, [effectiveImportPublicId, page]);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleExecuteDelete = async () => {
    if (!effectiveImportPublicId) return;
    setDeleteLoading(true);
    try {
      await statementImportApi.deleteStatementImport(effectiveImportPublicId);
      navigateTo('/upi/admin/statement-imports');
    } catch (err: any) {
      setError(err.message || 'Failed to delete statement import.');
      setDeleteModalOpen(false);
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="statement-imports" onNavigate={navigateTo} />
        <div style={{ textAlign: 'center', padding: '4rem 0' }}>
          <Loader2 size={36} className="spinner" color="#818cf8" />
          <p style={{ color: '#94a3b8', marginTop: '12px' }}>Loading statement import details...</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="statement-imports" onNavigate={navigateTo} />
        <div className="error-banner" style={{ margin: '24px 0' }}>
          <span>{error || 'Statement import record not found.'}</span>
        </div>
        <button onClick={() => navigateTo('/upi/admin/statement-imports')} className="btn btn-outline">
          ← Back to Statement Imports
        </button>
      </div>
    );
  }

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="statement-imports" onNavigate={navigateTo} />

      {/* Navigation Link */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <button
          onClick={() => navigateTo('/upi/admin/statement-imports')}
          className="btn btn-sm btn-outline"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} />
          <span>Back to Statement Imports</span>
        </button>
      </div>

      {/* Statement Summary Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div className="badge">
              <FileSpreadsheet size={14} />
              Statement Import Summary
            </div>
            <h1 className="page-title" style={{ fontSize: '1.45rem' }}>{detail.filename}</h1>
            <p className="page-subtitle" style={{ fontSize: '0.875rem' }}>
              Format: <span className="uppercase font-semibold" style={{ color: '#f8fafc' }}>{detail.file_type}</span>
              {detail.selected_sheet_name && (
                <span> | Sheet: <span className="monospace" style={{ color: '#818cf8' }}>[{detail.selected_sheet_name}]</span></span>
              )}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {detail.status === 'COMPLETED' ? (
              <span className="status-pill active-pill">✓ Import Successful</span>
            ) : detail.status === 'COMPLETED_WITH_ERRORS' ? (
              <span className="status-pill inactive-pill">⚠ Completed with Warnings</span>
            ) : (
              <span className="status-pill archived-pill">{detail.status}</span>
            )}
            <button
              onClick={() => setDeleteModalOpen(true)}
              className="btn btn-sm btn-danger-outline"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              title="Delete this statement import and all its associated transactions"
            >
              <Trash2 size={14} />
              <span>Delete Import</span>
            </button>
          </div>
        </div>

        {/* User-friendly Stat Badges */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div className="summary-section" style={{ textAlign: 'center', padding: '12px' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>{detail.total_rows}</span>
            <span className="detail-label">Total Entries</span>
          </div>

          <div className="summary-section" style={{ textAlign: 'center', padding: '12px', background: 'rgba(16,185,129,0.1)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#34d399' }}>+{detail.new_transactions}</span>
            <span className="detail-label" style={{ color: '#34d399' }}>New Transactions</span>
          </div>

          <div className="summary-section" style={{ textAlign: 'center', padding: '12px', background: 'rgba(245,158,11,0.1)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24' }}>{detail.duplicate_rows}</span>
            <span className="detail-label" style={{ color: '#fbbf24' }}>Duplicates Skipped</span>
          </div>

          <div className="summary-section" style={{ textAlign: 'center', padding: '12px' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#cbd5e1' }}>{detail.valid_rows}</span>
            <span className="detail-label">Valid Entries</span>
          </div>

          <div className="summary-section" style={{ textAlign: 'center', padding: '12px' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#94a3b8' }}>{detail.rows_without_reference}</span>
            <span className="detail-label">Missing Ref Code</span>
          </div>

          <div className="summary-section" style={{ textAlign: 'center', padding: '12px', background: 'rgba(239,68,68,0.1)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#f87171' }}>{detail.invalid_rows}</span>
            <span className="detail-label" style={{ color: '#f87171' }}>Unparsed Rows</span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', color: '#94a3b8', borderTop: '1px solid var(--border-color)', paddingTop: '14px', marginBottom: '16px' }}>
          <span>Uploaded By: <strong style={{ color: '#e2e8f0' }}>{detail.imported_by_name}</strong></span>
          <span>Date Completed: <strong style={{ color: '#e2e8f0' }}>{detail.completed_at ? new Date(detail.completed_at).toLocaleString() : '-'}</strong></span>
        </div>

        {/* Collapsible Technical / IT Support Info */}
        <details style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px 14px', cursor: 'pointer' }}>
          <summary style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>⚙ Technical System Information (for IT Support)</span>
          </summary>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px', marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div>
              <span className="detail-label" style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                <Hash size={12} /> File SHA-256 Checksum:
              </span>
              <span className="monospace" style={{ color: '#cbd5e1', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                {detail.file_checksum_sha256}
              </span>
            </div>

            <div>
              <span className="detail-label" style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                <Database size={12} /> Canonical Mapping Hash:
              </span>
              <span className="monospace" style={{ color: '#cbd5e1', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                {detail.canonical_mapping_hash}
              </span>
            </div>
          </div>
        </details>
      </div>

      {/* Bank Transactions Section */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>
              Imported Bank Transactions ({totalTxns})
            </h3>
            <span className="field-hint">List of individual payment entries recorded from this statement file.</span>
          </div>
          {txnsLoading && <Loader2 size={16} className="spinner" color="#818cf8" />}
        </div>

        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Txn Date & Time</th>
                <th>Type</th>
                <th style={{ textAlign: 'right' }}>Amount (₹)</th>
                <th>Payment Reference Code</th>
                <th>Bank UTR</th>
                <th>Payer Name</th>
              </tr>
            </thead>
            <tbody>
              {txnsLoading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
                    Loading transactions...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
                    No new bank transactions created under this statement import.
                  </td>
                </tr>
              ) : (
                transactions.map((txn) => (
                  <tr key={txn.public_id}>
                    <td style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
                      {txn.transaction_at ? new Date(txn.transaction_at).toLocaleString() : '-'}
                    </td>
                    <td>
                      {txn.direction === 'CREDIT' ? (
                        <span className="status-pill active-pill" style={{ fontSize: '0.7rem' }}>CREDIT</span>
                      ) : (
                        <span className="status-pill archived-pill" style={{ fontSize: '0.7rem' }}>DEBIT</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="amount-highlight font-semibold" style={{ fontFamily: 'monospace', fontSize: '0.95rem' }}>
                        ₹{(txn.amount_inr ?? 0).toLocaleString()}
                      </span>
                    </td>
                    <td>
                      <span className="monospace font-bold" style={{ color: '#a5b4fc', fontSize: '0.85rem' }}>
                        {txn.reference_id || <span style={{ color: '#64748b', fontStyle: 'italic', fontWeight: 400 }}>(None)</span>}
                      </span>
                    </td>
                    <td>
                      <span className="monospace" style={{ color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                        {txn.utr || <span style={{ color: '#64748b', fontStyle: 'italic', fontWeight: 400 }}>(None)</span>}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{txn.counterparty_name || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Transactions Pagination */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.15)' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Page {page} of {totalPages} ({totalTxns} transactions)
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

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ color: '#f87171' }}>Delete Statement Import</h3>
              <button onClick={() => setDeleteModalOpen(false)} className="icon-btn">
                <X size={16} />
              </button>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <p style={{ color: '#e2e8f0', fontSize: '0.95rem', marginBottom: '12px' }}>
                Are you sure you want to delete this imported statement file?
              </p>
              <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '12px 16px', borderRadius: '8px', color: '#fca5a5', fontSize: '0.9rem', marginBottom: '16px' }}>
                <strong>{detail.filename}</strong>
                <div style={{ fontSize: '0.8rem', color: '#f87171', marginTop: '4px' }}>
                  Total entries: {detail.total_rows} | New transactions created: +{detail.new_transactions}
                </div>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                This action will permanently delete this statement import record and all {detail.new_transactions} bank transactions recorded from it.
              </p>
            </div>

            <div className="modal-footer">
              <button
                onClick={() => setDeleteModalOpen(false)}
                disabled={deleteLoading}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteDelete}
                disabled={deleteLoading}
                className="btn btn-danger-outline"
                style={{ background: '#ef4444', color: '#ffffff', borderColor: '#ef4444', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {deleteLoading ? (
                  <>
                    <Loader2 size={16} className="spinner" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    <span>Delete Statement Import</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminStatementImportDetailPage;
