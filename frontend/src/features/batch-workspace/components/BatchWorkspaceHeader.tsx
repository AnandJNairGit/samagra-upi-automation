import React from 'react';
import { ArrowLeft, Check, Copy, RefreshCw } from 'lucide-react';
import { Batch, BatchSummary } from '../../../types/batch';

interface BatchWorkspaceHeaderProps {
  batch: Batch;
  summary: BatchSummary;
  onNavigate: (path: string) => void;
  copiedLink: boolean;
  onCopyLink: () => void;
  onRefresh: () => void;
}

export const BatchWorkspaceHeader: React.FC<BatchWorkspaceHeaderProps> = ({
  batch,
  onNavigate,
  copiedLink,
  onCopyLink,
  onRefresh
}) => {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
        <button onClick={() => onNavigate('/upi/admin/batches')} className="btn-link" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#818cf8', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
          <ArrowLeft size={14} /> Batches
        </button>
        <span>/</span>
        <span>{batch.course_name || 'Course'}</span>
      </div>

      <div className="workspace-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 className="page-title" style={{ margin: 0 }}>{batch.name}</h1>
            <span className={`status-pill ${batch.status === 'ACTIVE' ? 'active-pill' : batch.status === 'INACTIVE' ? 'inactive-pill' : 'archived-pill'}`}>
              {batch.status}
            </span>
          </div>
          <p className="page-subtitle" style={{ marginTop: '4px' }}>
            {batch.course_name} — Fee: <strong style={{ color: '#38bdf8' }}>{formatINR(batch.amount_inr)}</strong>
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={onCopyLink} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {copiedLink ? <Check size={16} color="#34d399" /> : <Copy size={16} />}
            <span>{copiedLink ? 'Copied Link!' : 'Copy Registration Link'}</span>
          </button>
          <button onClick={onRefresh} className="icon-btn" title="Refresh Workspace">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>
    </>
  );
};
