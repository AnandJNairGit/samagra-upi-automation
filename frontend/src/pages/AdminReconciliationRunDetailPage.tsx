import React, { useEffect, useState } from 'react';
import AdminNav from '../components/AdminNav';
import { reconciliationApi } from '../services/reconciliationApi';
import {
  ReconciliationResultDetailResponse,
  ReconciliationResultResponse,
  ReconciliationRunResponse,
} from '../types/reconciliation';
import {
  GitCompare,
  ArrowLeft,
  RefreshCw,
  Loader2,
  AlertCircle,
  FileText,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Check,
  Minus,
} from 'lucide-react';

interface AdminReconciliationRunDetailPageProps {
  runPublicId: string;
  onNavigate?: (path: string) => void;
}

export const AdminReconciliationRunDetailPage: React.FC<AdminReconciliationRunDetailPageProps> = ({
  runPublicId,
  onNavigate,
}) => {
  const navigateTo = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  const [run, setRun] = useState<ReconciliationRunResponse | null>(null);
  const [results, setResults] = useState<ReconciliationResultResponse[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [activeSearch, setActiveSearch] = useState<string>('');

  // Inspection Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ReconciliationResultDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchRunDetail = async () => {
    try {
      const res = await reconciliationApi.getReconciliationRun(runPublicId);
      setRun(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reconciliation run details.');
    }
  };

  const fetchResults = async (targetPage: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await reconciliationApi.getReconciliationResults(
        runPublicId,
        statusFilter || undefined,
        undefined,
        activeSearch || undefined,
        targetPage,
        20
      );
      setResults(res.items);
      setTotalCount(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reconciliation results.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRunDetail();
  }, [runPublicId]);

  useEffect(() => {
    fetchResults(page);
  }, [runPublicId, statusFilter, activeSearch, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setActiveSearch(searchInput.trim());
  };

  const handleOpenDetailModal = async (resultPublicId: string) => {
    setModalOpen(true);
    setDetailLoading(true);
    setDetailItem(null);
    try {
      const res = await reconciliationApi.getReconciliationResultDetail(resultPublicId);
      setDetailItem(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load result inspection details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'MATCHED':
        return <span className="status-pill active-pill">Matched ✓</span>;
      case 'AMOUNT_MISMATCH':
        return <span className="status-pill archived-pill" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>Amount Mismatch</span>;
      case 'UTR_MISMATCH':
        return <span className="status-pill pending-pill" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>UTR Mismatch</span>;
      case 'UNKNOWN_REFERENCE':
        return <span className="status-pill" style={{ background: 'rgba(96, 165, 250, 0.15)', color: '#60a5fa', border: '1px solid rgba(96,165,250,0.3)' }}>Unknown Reference</span>;
      case 'NO_REFERENCE':
        return <span className="status-pill" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.3)' }}>No Reference</span>;
      case 'DUPLICATE_TRANSACTION':
        return <span className="status-pill" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)' }}>Duplicate Transaction</span>;
      case 'UNMATCHED':
        return <span className="status-pill archived-pill">Non-Credit</span>;
      default:
        return <span className="status-pill">{status}</span>;
    }
  };

  const renderIndicator = (val?: boolean | null) => {
    if (val === true) {
      return <span style={{ color: '#34d399', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '2px' }}><Check size={14} /> Yes</span>;
    }
    if (val === false) {
      return <span style={{ color: '#f87171', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '2px' }}><X size={14} /> No</span>;
    }
    return <span style={{ color: '#94a3b8', display: 'inline-flex', alignItems: 'center', gap: '2px' }}><Minus size={14} /> N/A</span>;
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="reconciliation" onNavigate={navigateTo} />

      <div style={{ marginBottom: '16px' }}>
        <button
          onClick={() => navigateTo('/upi/admin/reconciliation')}
          className="btn btn-outline btn-sm"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} />
          <span>Back to Reconciliation Runs</span>
        </button>
      </div>

      {run && (
        <header className="page-header" style={{ marginBottom: '20px' }}>
          <div>
            <div className="badge">
              <GitCompare size={14} />
              Reconciliation Run Detail
            </div>
            <h1 className="page-title">{run.filename}</h1>
            <p className="page-subtitle">
              Executed on {new Date(run.started_at).toLocaleString()} • Status: <span style={{ color: '#34d399', fontWeight: 600 }}>{run.status}</span>
            </p>
          </div>

          <div className="page-actions">
            <button onClick={() => { fetchRunDetail(); fetchResults(page); }} className="btn btn-outline">
              <RefreshCw size={14} className={loading ? 'spinner' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </header>
      )}

      {error && (
        <div className="error-banner" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} color="#ef4444" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Summary Cards */}
      {run && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '24px' }}>
          <div className="summary-section" style={{ padding: '12px' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
              {run.total_transactions}
            </span>
            <span className="detail-label">Total Txns</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#34d399' }}>
              {run.matched_count}
            </span>
            <span className="detail-label" style={{ color: '#34d399' }}>Matched ✓</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#f87171' }}>
              {run.amount_mismatch_count}
            </span>
            <span className="detail-label" style={{ color: '#f87171' }}>Amt Mismatch</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24' }}>
              {run.utr_mismatch_count}
            </span>
            <span className="detail-label" style={{ color: '#fbbf24' }}>UTR Mismatch</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#60a5fa' }}>
              {run.unknown_reference_count}
            </span>
            <span className="detail-label" style={{ color: '#60a5fa' }}>Unknown Ref</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(148,163,184,0.1)', border: '1px solid rgba(148,163,184,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#94a3b8' }}>
              {run.no_reference_count}
            </span>
            <span className="detail-label" style={{ color: '#94a3b8' }}>No Reference</span>
          </div>

          <div className="summary-section" style={{ padding: '12px', background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.2)' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#c084fc' }}>
              {run.duplicate_transaction_count}
            </span>
            <span className="detail-label" style={{ color: '#c084fc' }}>Duplicate Txns</span>
          </div>

          <div className="summary-section" style={{ padding: '12px' }}>
            <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#64748b' }}>
              {run.unmatched_count}
            </span>
            <span className="detail-label">Non-Credit</span>
          </div>
        </div>
      )}

      {/* Filter & Search Toolbar */}
      <div className="card" style={{ padding: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'space-between', alignItems: 'center' }}>
          {/* Status Filter Buttons */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            <button
              onClick={() => { setStatusFilter(''); setPage(1); }}
              className={`btn btn-sm ${statusFilter === '' ? 'btn-primary' : 'btn-outline'}`}
            >
              All ({run?.total_transactions || 0})
            </button>
            <button
              onClick={() => { setStatusFilter('MATCHED'); setPage(1); }}
              className={`btn btn-sm ${statusFilter === 'MATCHED' ? 'btn-primary' : 'btn-outline'}`}
            >
              Matched ({run?.matched_count || 0})
            </button>
            <button
              onClick={() => { setStatusFilter('AMOUNT_MISMATCH'); setPage(1); }}
              className={`btn btn-sm ${statusFilter === 'AMOUNT_MISMATCH' ? 'btn-primary' : 'btn-outline'}`}
            >
              Amt Mismatch ({run?.amount_mismatch_count || 0})
            </button>
            <button
              onClick={() => { setStatusFilter('UTR_MISMATCH'); setPage(1); }}
              className={`btn btn-sm ${statusFilter === 'UTR_MISMATCH' ? 'btn-primary' : 'btn-outline'}`}
            >
              UTR Mismatch ({run?.utr_mismatch_count || 0})
            </button>
            <button
              onClick={() => { setStatusFilter('UNKNOWN_REFERENCE'); setPage(1); }}
              className={`btn btn-sm ${statusFilter === 'UNKNOWN_REFERENCE' ? 'btn-primary' : 'btn-outline'}`}
            >
              Unknown Ref ({run?.unknown_reference_count || 0})
            </button>
            <button
              onClick={() => { setStatusFilter('NO_REFERENCE'); setPage(1); }}
              className={`btn btn-sm ${statusFilter === 'NO_REFERENCE' ? 'btn-primary' : 'btn-outline'}`}
            >
              No Ref ({run?.no_reference_count || 0})
            </button>
          </div>

          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '6px' }}>
            <input
              type="text"
              placeholder="Search Ref Code, UTR, Payer..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="form-input"
              style={{ width: '220px', padding: '6px 10px', fontSize: '0.85rem' }}
            />
            <button type="submit" className="btn btn-sm btn-outline">
              <Search size={14} />
            </button>
          </form>
        </div>
      </div>

      {/* Results Table */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Reconciliation Results ({totalCount})</h2>
          {loading && <Loader2 size={16} className="spinner" color="#818cf8" />}
        </div>

        {loading && results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0' }}>
            <Loader2 size={32} className="spinner" color="#818cf8" />
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Loading reconciliation results...</p>
          </div>
        ) : results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <GitCompare size={36} color="#64748b" style={{ margin: '0 auto 10px' }} />
            <p style={{ color: '#e2e8f0', fontSize: '0.95rem', fontWeight: 600 }}>No matching reconciliation results found.</p>
            <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>Try clearing your search or status filter.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Reference Code</th>
                  <th>Classification</th>
                  <th style={{ textAlign: 'right' }}>Bank Amount</th>
                  <th style={{ textAlign: 'right' }}>Expected Amount</th>
                  <th>Bank UTR</th>
                  <th>Submitted UTR</th>
                  <th>Explanation</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {results.map((res) => (
                  <tr key={res.public_id}>
                    <td>
                      <span className="font-semibold" style={{ color: res.bank_reference_id ? '#a5b4fc' : '#94a3b8', fontFamily: 'monospace' }}>
                        {res.bank_reference_id || '(No Ref)'}
                      </span>
                    </td>
                    <td>{renderStatusBadge(res.status)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }} className="amount-highlight font-semibold">
                      ₹{res.bank_amount_inr ?? 0}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: res.expected_amount_inr ? '#f8fafc' : '#64748b' }}>
                      {res.expected_amount_inr ? `₹${res.expected_amount_inr}` : '-'}
                    </td>
                    <td style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: '#38bdf8' }}>
                      {res.bank_utr || '-'}
                    </td>
                    <td style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: '#38bdf8' }}>
                      {res.submitted_utr || '-'}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={res.explanation}>
                      {res.explanation}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => handleOpenDetailModal(res.public_id)}
                        className="btn-action"
                      >
                        <FileText size={12} />
                        <span>Inspect</span>
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
              Page {page} of {totalPages} ({totalCount} total entries)
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

      {/* Read-Only Inspection Modal (ZERO APPROVE/REJECT CONTROLS) */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <div>
                <h3>Reconciliation Result Evidence</h3>
                <span className="field-hint">Read-Only Audit Inspection (Phase 10)</span>
              </div>
              <button onClick={() => setModalOpen(false)} className="icon-btn">
                <X size={16} />
              </button>
            </div>

            {detailLoading ? (
              <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                <Loader2 size={32} className="spinner" color="#818cf8" />
                <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Loading result evidence...</p>
              </div>
            ) : detailItem ? (
              <div>
                <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span className="field-hint">Classification Result</span>
                    <div style={{ marginTop: '4px' }}>{renderStatusBadge(detailItem.status)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="field-hint">Reason Code</span>
                    <div style={{ fontFamily: 'monospace', fontWeight: 600, color: '#e2e8f0', fontSize: '0.85rem' }}>
                      {detailItem.reason_code}
                    </div>
                  </div>
                </div>

                <div className="error-banner" style={{ background: 'rgba(99,102,241,0.1)', borderColor: 'rgba(99,102,241,0.3)', color: '#e0e7ff', marginBottom: '20px' }}>
                  <AlertCircle size={16} color="#818cf8" />
                  <span>{detailItem.explanation}</span>
                </div>

                {/* Evidence Flags Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px', background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                  <div>
                    <span className="field-hint" style={{ display: 'block' }}>Reference Match</span>
                    {renderIndicator(detailItem.reference_match)}
                  </div>
                  <div>
                    <span className="field-hint" style={{ display: 'block' }}>Amount Match</span>
                    {renderIndicator(detailItem.amount_match)}
                  </div>
                  <div>
                    <span className="field-hint" style={{ display: 'block' }}>UTR Match</span>
                    {renderIndicator(detailItem.utr_match)}
                  </div>
                </div>

                {/* Side-by-Side Comparison Details */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                  {/* Bank Transaction Data */}
                  <div className="summary-section" style={{ padding: '14px' }}>
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8', marginBottom: '10px', textTransform: 'uppercase' }}>
                      Imported Bank Transaction
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem' }}>
                      <div><span className="field-hint">Reference:</span> <span style={{ fontFamily: 'monospace', color: '#f8fafc' }}>{detailItem.bank_reference_id || '-'}</span></div>
                      <div><span className="field-hint">Amount:</span> <span style={{ fontFamily: 'monospace', color: '#34d399', fontWeight: 600 }}>₹{detailItem.bank_amount_inr ?? 0}</span></div>
                      <div><span className="field-hint">Bank UTR:</span> <span style={{ fontFamily: 'monospace', color: '#38bdf8' }}>{detailItem.bank_utr || '-'}</span></div>
                      <div><span className="field-hint">Payer Name:</span> <span style={{ color: '#e2e8f0' }}>{detailItem.bank_counterparty_name || '-'}</span></div>
                      <div><span className="field-hint">Date:</span> <span style={{ color: '#94a3b8' }}>{detailItem.bank_transaction_at ? new Date(detailItem.bank_transaction_at).toLocaleString() : '-'}</span></div>
                    </div>
                  </div>

                  {/* System Payment Session Data */}
                  <div className="summary-section" style={{ padding: '14px' }}>
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#a5b4fc', marginBottom: '10px', textTransform: 'uppercase' }}>
                      System Payment Session
                    </h4>
                    {detailItem.expected_reference_id ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem' }}>
                        <div><span className="field-hint">Reference:</span> <span style={{ fontFamily: 'monospace', color: '#f8fafc' }}>{detailItem.expected_reference_id}</span></div>
                        <div><span className="field-hint">Expected Amt:</span> <span style={{ fontFamily: 'monospace', color: '#f8fafc', fontWeight: 600 }}>₹{detailItem.expected_amount_inr}</span></div>
                        <div><span className="field-hint">Submitted UTR:</span> <span style={{ fontFamily: 'monospace', color: '#38bdf8' }}>{detailItem.submitted_utr || 'Not Submitted'}</span></div>
                        <div><span className="field-hint">Participant:</span> <span style={{ color: '#e2e8f0' }}>{detailItem.participant_name || '-'}</span></div>
                        <div><span className="field-hint">Session Status:</span> <span style={{ color: '#a5b4fc', fontWeight: 600 }}>{detailItem.payment_session_status}</span></div>
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>
                        No matching PaymentSession record found in database.
                      </p>
                    )}
                  </div>
                </div>

                <div className="modal-footer">
                  <button onClick={() => setModalOpen(false)} className="btn btn-outline" style={{ width: '100%' }}>
                    Close Inspection Window
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminReconciliationRunDetailPage;
