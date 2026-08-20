import React from 'react';
import { GitCompare, Loader2, Play, CheckCircle2, AlertTriangle, Eye } from 'lucide-react';
import { BatchSummary, Batch } from '../../../types/batch';
import { StatementImportListItem } from '../../../types/statementImport';
import { ReconciliationRunResponse, ReconciliationResultResponse, ReconciliationStatus } from '../../../types/reconciliation';

interface ReconciliationPanelProps {
  batch: Batch;
  summary: BatchSummary;
  imports: StatementImportListItem[];
  selectedStatementIdForRecon: string;
  setSelectedStatementIdForRecon: (val: string) => void;
  activeRun: ReconciliationRunResponse | null;
  reconResults: ReconciliationResultResponse[];
  reconResultsLoading: boolean;
  reconFilter: 'ALL' | 'MATCHED' | 'NOT_MATCHED';
  setReconFilter: (val: 'ALL' | 'MATCHED' | 'NOT_MATCHED') => void;
  startingRecon: boolean;
  handleExecuteReconciliation: () => void;
  openResultDetail: (resultPublicId: string) => void;
}

export const ReconciliationPanel: React.FC<ReconciliationPanelProps> = ({
  batch,
  summary,
  imports,
  selectedStatementIdForRecon,
  setSelectedStatementIdForRecon,
  activeRun,
  reconResults,
  reconResultsLoading,
  reconFilter,
  setReconFilter,
  startingRecon,
  handleExecuteReconciliation,
  openResultDetail
}) => {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const mapResultStatusToUI = (status: ReconciliationStatus | string) => {
    switch (status) {
      case 'MATCHED':
        return { badgeClass: 'active-pill', isMatched: true };
      case 'UNMATCHED':
      case 'AMOUNT_MISMATCH':
        return { badgeClass: 'archived-pill', isMatched: false };
      case 'UTR_MISMATCH':
      case 'DUPLICATE_TRANSACTION':
      case 'NO_REFERENCE':
      case 'UNKNOWN_REFERENCE':
        return { badgeClass: 'pending-pill', isMatched: false };
      default:
        return { badgeClass: 'inactive-pill', isMatched: false };
    }
  };

  return (
    <div>
      {/* Pre-Execution Control Card */}
      <div className="card" style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.05))', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
          <GitCompare size={20} color="#818cf8" />
          Reconcile Batch: {batch.name}
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 220px', gap: '1.5rem', alignItems: 'center' }}>
          <div>
            <label className="form-label">Select Imported Bank Statement File *</label>
            <select
              value={selectedStatementIdForRecon}
              onChange={(e) => setSelectedStatementIdForRecon(e.target.value)}
              className="form-input"
              style={{ background: 'var(--bg-secondary)', fontWeight: 600 }}
            >
              <option value="" disabled>Select Bank Statement...</option>
              {imports.map((imp) => (
                <option key={imp.public_id} value={imp.public_id}>
                  {imp.filename} ({imp.valid_rows} txns — {new Date(imp.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              Execution will match this batch's payment sessions (`{summary.payments_generated}` sessions) strictly against credits in the selected statement file.
            </p>
          </div>

          <div>
            <button
              onClick={handleExecuteReconciliation}
              disabled={startingRecon || !selectedStatementIdForRecon}
              className="btn btn-primary"
              style={{ width: '100%', height: '48px', fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              {startingRecon ? <Loader2 size={18} className="spinner" /> : <Play size={18} />}
              <span>{startingRecon ? 'Reconciling...' : 'Reconcile Batch'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Active Reconciliation Results View */}
      {activeRun && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h4>Reconciliation Results — {activeRun.filename}</h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Executed {new Date(activeRun.created_at).toLocaleString()}</p>
            </div>

            {/* Filter Toggles */}
            <div className="filter-pills">
              <button className={`filter-pill ${reconFilter === 'ALL' ? 'active' : ''}`} onClick={() => setReconFilter('ALL')}>
                All ({activeRun.total_transactions})
              </button>
              <button className={`filter-pill ${reconFilter === 'MATCHED' ? 'active' : ''}`} onClick={() => setReconFilter('MATCHED')}>
                ✓ Matched ({activeRun.matched_count})
              </button>
              <button className={`filter-pill ${reconFilter === 'NOT_MATCHED' ? 'active' : ''}`} onClick={() => setReconFilter('NOT_MATCHED')}>
                ⚠ Not Matched ({activeRun.total_transactions - activeRun.matched_count})
              </button>
            </div>
          </div>

          {/* Summary Status Banner */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: activeRun.matched_count === activeRun.total_transactions ? 'rgba(52, 211, 153, 0.12)' : 'rgba(245, 158, 11, 0.12)',
              border: `1px solid ${activeRun.matched_count === activeRun.total_transactions ? 'rgba(52, 211, 153, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
            }}
          >
            {activeRun.matched_count === activeRun.total_transactions ? (
              <CheckCircle2 size={20} color="#34d399" />
            ) : (
              <AlertTriangle size={20} color="#f59e0b" />
            )}
            <div>
              <strong style={{ color: activeRun.matched_count === activeRun.total_transactions ? '#34d399' : '#f59e0b' }}>
                {activeRun.matched_count} of {activeRun.total_transactions} transactions matched cleanly.
              </strong>
              <span style={{ fontSize: '0.85rem', marginLeft: '8px', color: 'var(--text-secondary)' }}>
                ({activeRun.amount_mismatch_count} Amount Mismatches, {activeRun.utr_mismatch_count} UTR Mismatches, {activeRun.unknown_reference_count} Unknown References)
              </span>
            </div>
          </div>

          {/* Results Table */}
          {reconResultsLoading ? (
            <Loader2 size={24} className="spinner" />
          ) : (
            <div className="table-responsive">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Classification Reason</th>
                    <th>Bank Reference</th>
                    <th>Bank Amount</th>
                    <th>Expected Ref</th>
                    <th>Expected Amount</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reconResults
                    .filter((r) => {
                      if (reconFilter === 'MATCHED') return r.status === 'MATCHED';
                      if (reconFilter === 'NOT_MATCHED') return r.status !== 'MATCHED';
                      return true;
                    })
                    .map((res) => {
                      const uiStatus = mapResultStatusToUI(res.status);
                      return (
                        <tr key={res.public_id}>
                          <td>
                            <span className={`status-pill ${uiStatus.badgeClass}`}>
                              {uiStatus.isMatched ? '✓ Matched' : '⚠ Not Matched'}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontWeight: 500 }}>{res.explanation}</span>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{res.reason_code}</div>
                          </td>
                          <td className="monospace font-semibold" style={{ color: '#38bdf8' }}>{res.bank_reference_id || '—'}</td>
                          <td className="monospace">{res.bank_amount_inr ? formatINR(res.bank_amount_inr) : '—'}</td>
                          <td className="monospace font-semibold">{res.expected_reference_id || '—'}</td>
                          <td className="monospace">{res.expected_amount_inr ? formatINR(res.expected_amount_inr) : '—'}</td>
                          <td>
                            <button onClick={() => openResultDetail(res.public_id)} className="btn-action">
                              <Eye size={14} /> Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
