import React from 'react';
import { CreditCard, FileSpreadsheet, GitCompare } from 'lucide-react';
import { WorkspaceTab } from '../hooks/useBatchWorkspace';

interface BatchWorkspaceTabsProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  paymentsGeneratedCount: number;
}

export const BatchWorkspaceTabs: React.FC<BatchWorkspaceTabsProps> = ({
  activeTab,
  onTabChange,
  paymentsGeneratedCount
}) => {
  return (
    <div className="workspace-tab-bar" style={{ display: 'flex', gap: '8px', marginTop: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
      <button
        className={`nav-tab ${activeTab === 'payments' ? 'active' : ''}`}
        onClick={() => onTabChange('payments')}
        style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'payments' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'payments' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
      >
        <CreditCard size={16} />
        <span>Payments & Overview ({paymentsGeneratedCount})</span>
      </button>

      <button
        className={`nav-tab ${activeTab === 'bank-transactions' ? 'active' : ''}`}
        onClick={() => onTabChange('bank-transactions')}
        style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'bank-transactions' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'bank-transactions' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
      >
        <FileSpreadsheet size={16} />
        <span>Bank Transactions</span>
      </button>

      <button
        className={`nav-tab ${activeTab === 'reconciliation' ? 'active' : ''}`}
        onClick={() => onTabChange('reconciliation')}
        style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'reconciliation' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'reconciliation' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
      >
        <GitCompare size={16} />
        <span>Reconciliation</span>
      </button>
    </div>
  );
};
