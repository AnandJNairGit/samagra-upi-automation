import React from 'react';
import { ArrowLeft, Loader2, AlertTriangle, CreditCard, X, AlertCircle } from 'lucide-react';
import { AdminNav } from '../../../components/AdminNav';
import { useBatchWorkspace } from '../hooks/useBatchWorkspace';
import { useBatchPayments } from '../hooks/useBatchPayments';
import { useBatchReconciliation } from '../hooks/useBatchReconciliation';
import { useStatementImports } from '../hooks/useStatementImports';
import { usePaymentInspection } from '../hooks/usePaymentInspection';

import { BatchWorkspaceHeader } from './BatchWorkspaceHeader';
import { BatchWorkspaceTabs } from './BatchWorkspaceTabs';
import { PaymentsTable } from './PaymentsTable';
import { ReconciliationPanel } from './ReconciliationPanel';
import { StatementImportsPanel } from './StatementImportsPanel';
import { ReconciliationInspectionModal } from './ReconciliationInspectionModal';

interface BatchWorkspaceProps {
  batchPublicId: string;
  onNavigate: (path: string) => void;
  initialTab?: 'overview' | 'payments' | 'bank-transactions' | 'reconciliation';
}

export const BatchWorkspace: React.FC<BatchWorkspaceProps> = ({
  batchPublicId,
  onNavigate,
  initialTab = 'payments',
}) => {
  // 1. Workspace Shell State
  const {
    activeTab,
    setActiveTab,
    batch,
    summary,
    loading: workspaceLoading,
    error: workspaceError,
    copiedLink,
    loadBatchHeader,
    copyRegistrationLink
  } = useBatchWorkspace(batchPublicId, initialTab);

  // 2. Statement Imports
  const importsHook = useStatementImports(batchPublicId);

  // 3. Batch Reconciliation
  const reconHook = useBatchReconciliation(batchPublicId, loadBatchHeader);

  // 4. Batch Payments
  const paymentsHook = useBatchPayments(batchPublicId, async (run) => {
    // When a match is triggered from the Payments Table
    await reconHook.loadRunResults(run);
    await reconHook.loadReconHistory();
    await loadBatchHeader();
  });

  // 5. Payment & Reconciliation Inspection
  const inspectionHook = usePaymentInspection();

  if (workspaceLoading) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="batches" onNavigate={onNavigate} />
        <div className="card loading-card" style={{ marginTop: '2rem' }}>
          <Loader2 size={32} className="spinner" color="#818cf8" />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Opening Batch Workspace...</p>
        </div>
      </div>
    );
  }

  if (workspaceError || !batch || !summary) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="batches" onNavigate={onNavigate} />
        <div className="card error-card" style={{ marginTop: '2rem' }}>
          <AlertTriangle size={24} color="#ef4444" />
          <h3>Workspace Load Error</h3>
          <p>{workspaceError || 'Batch record not found.'}</p>
          <button onClick={() => onNavigate('/upi/admin/batches')} className="btn btn-outline" style={{ marginTop: '1rem' }}>
            <ArrowLeft size={16} /> Back to Batches
          </button>
        </div>
      </div>
    );
  }

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="batches" onNavigate={onNavigate} />

      {/* Cohort Workspace Header Banner */}
      <div className="card workspace-header-card" style={{ marginBottom: '1.5rem', padding: '1.5rem' }}>
        <BatchWorkspaceHeader
          batch={batch}
          summary={summary}
          onNavigate={onNavigate}
          copiedLink={copiedLink}
          onCopyLink={copyRegistrationLink}
          onRefresh={loadBatchHeader}
        />

        <BatchWorkspaceTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          paymentsGeneratedCount={summary.payments_generated}
        />
      </div>

      {/* TAB 1: PAYMENTS & OVERVIEW */}
      {activeTab === 'payments' && (
        <PaymentsTable
          summary={summary}
          payments={paymentsHook.payments}
          paymentsLoading={paymentsHook.paymentsLoading}
          paymentSearch={paymentsHook.paymentSearch}
          setPaymentSearch={paymentsHook.setPaymentSearch}
          paymentStatusFilter={paymentsHook.paymentStatusFilter}
          setPaymentStatusFilter={paymentsHook.setPaymentStatusFilter}
          selectedStatementIdForPaymentsMatch={paymentsHook.selectedStatementIdForPaymentsMatch}
          setSelectedStatementIdForPaymentsMatch={paymentsHook.setSelectedStatementIdForPaymentsMatch}
          matchingInPaymentsTable={paymentsHook.matchingInPaymentsTable}
          loadPayments={paymentsHook.loadPayments}
          handleMatchInPaymentsTable={paymentsHook.handleMatchInPaymentsTable}
          
          imports={importsHook.imports}
          reconResultsBySession={reconHook.reconResultsBySession}
          onInspectReconResult={inspectionHook.openReconciliationDetail}
          onInspectPaymentSession={inspectionHook.openPaymentDetail}
          onInspectApprovedSession={inspectionHook.openReconciliationDetailBySession}
        />
      )}

      {/* TAB 2: BANK TRANSACTIONS */}
      {activeTab === 'bank-transactions' && (
        <StatementImportsPanel {...importsHook} />
      )}

      {/* TAB 3: RECONCILIATION */}
      {activeTab === 'reconciliation' && (
        <ReconciliationPanel
          batch={batch}
          summary={summary}
          imports={importsHook.imports}
          selectedStatementIdForRecon={reconHook.selectedStatementIdForRecon}
          setSelectedStatementIdForRecon={reconHook.setSelectedStatementIdForRecon}
          activeRun={reconHook.activeRun}
          reconResults={reconHook.reconResults}
          reconResultsLoading={reconHook.reconResultsLoading}
          reconFilter={reconHook.reconFilter}
          setReconFilter={reconHook.setReconFilter}
          startingRecon={reconHook.startingRecon}
          handleExecuteReconciliation={reconHook.handleExecuteReconciliation}
          openResultDetail={inspectionHook.openReconciliationDetail}
        />
      )}

      {/* Modals & Drawers */}
      
      {/* 1. Reconciliation Inspection Modal */}
      <ReconciliationInspectionModal
        isOpen={inspectionHook.isReconModalOpen}
        onClose={inspectionHook.closeInspection}
        detail={inspectionHook.selectedReconResult}
        loading={inspectionHook.reconLoading}
        error={inspectionHook.reconError}
      />

      {/* 2. Payment Session Drawer (Standalone) */}
      {inspectionHook.isPaymentDrawerOpen && inspectionHook.selectedPayment && (
        <div
          className="modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) inspectionHook.closeInspection();
          }}
        >
          <div className="modal-card" style={{ maxWidth: '580px', background: '#0f172a', border: '1px solid rgba(129, 140, 248, 0.3)' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CreditCard size={20} color="#818cf8" />
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Payment Session Inspection</h3>
              </div>
              <button onClick={inspectionHook.closeInspection} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '0.5rem 0' }}>
              <div
                style={{
                  background: 'rgba(59, 130, 246, 0.1)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '0.85rem',
                  color: '#93c5fd',
                }}
              >
                <AlertCircle size={18} color="#60a5fa" style={{ flexShrink: 0 }} />
                <span>This payment session has not yet been compared against an imported statement.</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.875rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Participant:</span>
                  <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                    {inspectionHook.selectedPayment.participant.full_name} ({inspectionHook.selectedPayment.participant.phone})
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Email:</span>
                  <span style={{ color: '#e2e8f0' }}>{inspectionHook.selectedPayment.participant.email}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Reference ID:</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' }}>{inspectionHook.selectedPayment.payment.reference_id}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Amount:</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#34d399' }}>{formatINR(inspectionHook.selectedPayment.payment.amount_inr)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Session Status:</span>
                  <span className={`status-pill ${inspectionHook.selectedPayment.payment.status === 'APPROVED' ? 'active-pill' : inspectionHook.selectedPayment.payment.status === 'SUBMITTED' ? 'inactive-pill' : 'archived-pill'}`}>
                    {inspectionHook.selectedPayment.payment.status}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                  <span style={{ color: '#94a3b8' }}>Submitted UTR:</span>
                  <span style={{ fontFamily: 'monospace', color: '#e2e8f0' }}>{inspectionHook.selectedPayment.current_submission?.utr || 'Not Submitted (Optional)'}</span>
                </div>
                {inspectionHook.selectedPayment.current_submission && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                    <span style={{ color: '#94a3b8' }}>Submission Status:</span>
                    <span style={{ color: '#e2e8f0' }}>{inspectionHook.selectedPayment.current_submission.status}</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Created Date:</span>
                  <span style={{ color: '#94a3b8' }}>{new Date(inspectionHook.selectedPayment.payment.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="modal-footer" style={{ marginTop: '16px' }}>
              <button onClick={inspectionHook.closeInspection} className="btn btn-outline">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
