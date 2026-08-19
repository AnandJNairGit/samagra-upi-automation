import React, { useEffect, useState, useMemo } from 'react';
import { AdminNav } from '../components/AdminNav';
import { getBatch, getBatchSummary } from '../services/batchApi';
import { fetchAdminPayments, fetchAdminPaymentDetail } from '../services/adminPaymentApi';
import { statementImportApi } from '../services/statementImportApi';
import { reconciliationApi } from '../services/reconciliationApi';
import { Batch, BatchSummary } from '../types/batch';
import { AdminPaymentListItem, AdminPaymentDetailResponse } from '../types/adminPayment';
import {
  StatementImportListItem,
  ImportPreviewResponse,
  BankTransactionItem,
  HeaderItem,
  ImportSummaryResponse,
  StatementColumnMapping,
} from '../types/statementImport';
import { ReconciliationRunResponse, ReconciliationResultResponse, ReconciliationResultDetailResponse } from '../types/reconciliation';
import { config } from '../core/config';
import {
  CreditCard,
  FileSpreadsheet,
  GitCompare,
  ArrowLeft,
  Copy,
  Check,
  RefreshCw,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Search,
  Eye,
  X,
  Upload,
  Play,
  Plus,
  Trash2,
} from 'lucide-react';

interface AdminBatchWorkspacePageProps {
  batchPublicId: string;
  onNavigate: (path: string) => void;
  initialTab?: 'overview' | 'payments' | 'bank-transactions' | 'reconciliation';
}

export const AdminBatchWorkspacePage: React.FC<AdminBatchWorkspacePageProps> = ({
  batchPublicId,
  onNavigate,
  initialTab = 'payments',
}) => {
  const [activeTab, setActiveTab] = useState<'payments' | 'bank-transactions' | 'reconciliation'>(
    initialTab === 'overview' ? 'payments' : (initialTab as any)
  );
  
  // Batch & Summary State
  const [batch, setBatch] = useState<Batch | null>(null);
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  // Payments Tab State
  const [payments, setPayments] = useState<AdminPaymentListItem[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(false);
  const [paymentSearch, setPaymentSearch] = useState('');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('');
  const [selectedPayment, setSelectedPayment] = useState<AdminPaymentDetailResponse | null>(null);

  // Direct Match from Payments Table Header State
  const [selectedStatementIdForPaymentsMatch, setSelectedStatementIdForPaymentsMatch] = useState<string>('');
  const [matchingInPaymentsTable, setMatchingInPaymentsTable] = useState<boolean>(false);

  // Bank Transactions / Statement Imports Tab State
  const [imports, setImports] = useState<StatementImportListItem[]>([]);
  const [importsLoading, setImportsLoading] = useState(false);
  const [selectedImportId, setSelectedImportId] = useState<string | null>(null);
  const [importTxns, setImportTxns] = useState<BankTransactionItem[]>([]);
  const [txnsLoading, setTxnsLoading] = useState(false);

  // 5-Step Import Wizard Modal State
  const [wizardOpen, setWizardOpen] = useState(false);
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [headerRowIndex, setHeaderRowIndex] = useState(1);
  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [wizardError, setWizardError] = useState<string | null>(null);

  // Column mapping selection state (column_index based)
  const [refColIdx, setRefColIdx] = useState<number | ''>('');
  const [amtColIdx, setAmtColIdx] = useState<number | ''>('');
  const [dateColIdx, setDateColIdx] = useState<number | ''>('');
  const [dirColIdx, setDirColIdx] = useState<number | ''>('');
  const [utrColIdx, setUtrColIdx] = useState<number | ''>('');
  const [cpColIdx, setCpColIdx] = useState<number | ''>('');
  const [descColIdx, setDescColIdx] = useState<number | ''>('');

  // Step 5 Result State
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummaryResponse | null>(null);

  // Statement Delete Confirmation Modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<StatementImportListItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Reconciliation Tab State
  const [selectedStatementIdForRecon, setSelectedStatementIdForRecon] = useState<string>('');
  const [activeRun, setActiveRun] = useState<ReconciliationRunResponse | null>(null);
  const [reconResults, setReconResults] = useState<ReconciliationResultResponse[]>([]);
  const [reconResultsLoading, setReconResultsLoading] = useState(false);
  const [reconFilter, setReconFilter] = useState<'ALL' | 'MATCHED' | 'NOT_MATCHED'>('ALL');
  const [startingRecon, setStartingRecon] = useState(false);
  const [selectedResultDetail, setSelectedResultDetail] = useState<ReconciliationResultDetailResponse | null>(null);

  // Map Reconciliation Results by Payment Session Public ID & Reference Code
  const reconResultsBySession = useMemo(() => {
    const map: Record<string, ReconciliationResultResponse> = {};
    reconResults.forEach((res) => {
      if (res.payment_session_public_id) {
        map[res.payment_session_public_id] = res;
      }
      if (res.expected_reference_id) {
        map[res.expected_reference_id] = res;
      }
    });
    return map;
  }, [reconResults]);

  // Load Batch Header & Summary
  const loadBatchHeader = async () => {
    setLoading(true);
    setError(null);
    try {
      const [batchData, summaryData] = await Promise.all([
        getBatch(batchPublicId),
        getBatchSummary(batchPublicId),
      ]);
      setBatch(batchData);
      setSummary(summaryData);
    } catch (err: any) {
      setError(err.message || 'Failed to load batch workspace details.');
    } finally {
      setLoading(false);
    }
  };

  // Load Batch Payments
  const loadPayments = async () => {
    setPaymentsLoading(true);
    try {
      const res = await fetchAdminPayments({
        page: 1,
        page_size: 50,
        status: paymentStatusFilter || undefined,
        search: paymentSearch || undefined,
        batch_public_id: batchPublicId,
      });
      setPayments(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setPaymentsLoading(false);
    }
  };

  useEffect(() => {
    loadBatchHeader();
    loadPayments();
    loadReconHistory();
    loadImports();
  }, [batchPublicId]);

  // Load tab-specific data when tab changes
  useEffect(() => {
    if (activeTab === 'payments') {
      loadPayments();
    } else if (activeTab === 'bank-transactions') {
      loadImports();
    } else if (activeTab === 'reconciliation') {
      loadReconHistory();
      loadImports();
    }
  }, [activeTab]);

  // Load Statement Imports
  const loadImports = async () => {
    setImportsLoading(true);
    try {
      const res = await statementImportApi.getStatementImports(1, 50);
      setImports(res.items);
      if (res.items.length > 0 && !selectedImportId) {
        setSelectedImportId(res.items[0].public_id);
        loadImportTransactions(res.items[0].public_id);
      }
      if (res.items.length > 0 && !selectedStatementIdForRecon) {
        setSelectedStatementIdForRecon(res.items[0].public_id);
      }
      if (res.items.length > 0 && !selectedStatementIdForPaymentsMatch) {
        setSelectedStatementIdForPaymentsMatch(res.items[0].public_id);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setImportsLoading(false);
    }
  };

  // Load Transactions for selected import
  const loadImportTransactions = async (importPublicId: string) => {
    setSelectedImportId(importPublicId);
    setTxnsLoading(true);
    try {
      const res = await statementImportApi.getImportTransactions(importPublicId, 1, 50);
      setImportTxns(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setTxnsLoading(false);
    }
  };

  // Delete Statement Import Handler
  const handleExecuteDelete = async () => {
    if (!itemToDelete) return;
    setDeleteLoading(true);
    try {
      await statementImportApi.deleteStatementImport(itemToDelete.public_id);
      setDeleteModalOpen(false);
      setItemToDelete(null);
      await loadImports();
      await loadBatchHeader();
    } catch (err: any) {
      alert(err.message || 'Failed to delete statement import.');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Load Latest Reconciliation Run for this Batch
  const loadReconHistory = async () => {
    try {
      const res = await reconciliationApi.getReconciliationRuns(undefined, batchPublicId, 1, 20);
      if (res.items.length > 0 && !activeRun) {
        loadRunResults(res.items[0]);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  // Load Results for a specific Reconciliation Run
  const loadRunResults = async (run: ReconciliationRunResponse) => {
    setActiveRun(run);
    setReconResultsLoading(true);
    try {
      const res = await reconciliationApi.getReconciliationResults(run.public_id, undefined, undefined, undefined, 1, 500);
      setReconResults(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setReconResultsLoading(false);
    }
  };

  // Execute Direct Match from Payments Table Header
  const handleMatchInPaymentsTable = async () => {
    if (!selectedStatementIdForPaymentsMatch) {
      alert('Please select a bank statement transaction file from the dropdown first.');
      return;
    }
    setMatchingInPaymentsTable(true);
    try {
      const run = await reconciliationApi.startReconciliationRun(batchPublicId, selectedStatementIdForPaymentsMatch);
      await loadRunResults(run);
      await loadReconHistory();
      await loadBatchHeader();
      await loadPayments();
    } catch (err: any) {
      alert(`Matching failed: ${err.message}`);
    } finally {
      setMatchingInPaymentsTable(false);
    }
  };

  // Execute Batch Reconciliation from Reconciliation Tab
  const handleExecuteReconciliation = async () => {
    if (!selectedStatementIdForRecon) {
      alert('Please select a bank statement import file.');
      return;
    }
    setStartingRecon(true);
    try {
      const run = await reconciliationApi.startReconciliationRun(batchPublicId, selectedStatementIdForRecon);
      await loadRunResults(run);
      await loadReconHistory();
      await loadBatchHeader();
    } catch (err: any) {
      alert(`Reconciliation execution failed: ${err.message}`);
    } finally {
      setStartingRecon(false);
    }
  };

  // Open Payment Detail Drawer
  const openPaymentDetail = async (publicId: string) => {
    try {
      const detail = await fetchAdminPaymentDetail(publicId);
      setSelectedPayment(detail);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Open Reconciliation Result Detail
  const openResultDetail = async (resultPublicId: string) => {
    try {
      const detail = await reconciliationApi.getReconciliationResultDetail(resultPublicId);
      setSelectedResultDetail(detail);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Open Wizard Modal
  const openWizard = () => {
    setWizardOpen(true);
    setStep(1);
    setSelectedFile(null);
    setHeaderRowIndex(1);
    setPreviewData(null);
    setSelectedSheet('');
    setWizardError(null);
    setRefColIdx('');
    setAmtColIdx('');
    setDateColIdx('');
    setDirColIdx('');
    setUtrColIdx('');
    setCpColIdx('');
    setDescColIdx('');
    setImportSummary(null);
  };

  const closeWizard = () => {
    setWizardOpen(false);
    loadImports();
    loadBatchHeader();
  };

  // Step 1 Preview & Sheet Detection
  const handleFilePreview = async (sheetOverride?: string) => {
    if (!selectedFile) {
      setWizardError('Please select a CSV or Excel statement file.');
      return;
    }
    setPreviewLoading(true);
    setWizardError(null);

    try {
      const res = await statementImportApi.previewStatementImport(
        selectedFile,
        sheetOverride || selectedSheet || undefined,
        headerRowIndex
      );
      setPreviewData(res);
      if (res.selected_sheet_name) {
        setSelectedSheet(res.selected_sheet_name);
      }

      autoSuggestMappings(res.headers);

      if (res.available_sheets && res.available_sheets.length > 1 && !sheetOverride) {
        setStep(2);
      } else {
        setStep(3);
      }
    } catch (err: any) {
      setWizardError(err.message || 'Failed to process statement file. Please check file format.');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Auto-Suggest Mappings based on column headers
  const autoSuggestMappings = (headers: HeaderItem[]) => {
    headers.forEach((h) => {
      const name = h.header.toLowerCase();
      if (name.includes('remark') || name.includes('ref') || name.includes('txnid') || (name.includes('description') && name.includes('samagra'))) {
        setRefColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('amount') || name.includes('credit') || name.includes('inr')) {
        setAmtColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('date') || name.includes('time') || name.includes('created')) {
        setDateColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('type') || name.includes('dir') || name.includes('cr/dr')) {
        setDirColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('utr') || name.includes('rrn')) {
        setUtrColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('payer') || name.includes('name') || name.includes('counterparty')) {
        setCpColIdx((prev) => (prev === '' ? h.column_index : prev));
      } else if (name.includes('desc') || name.includes('note')) {
        setDescColIdx((prev) => (prev === '' ? h.column_index : prev));
      }
    });
  };

  const handleSheetChange = (sheetName: string) => {
    setSelectedSheet(sheetName);
    handleFilePreview(sheetName);
  };

  const handleProceedToPreviewTable = () => {
    if (refColIdx === '') {
      setWizardError('Please select which column contains the Payment Reference Code / Remarks.');
      return;
    }
    if (amtColIdx === '') {
      setWizardError('Please select which column contains the Amount.');
      return;
    }
    setWizardError(null);
    setStep(4);
  };

  const handleConfirmImport = async () => {
    if (!previewData) return;
    if (refColIdx === '' || amtColIdx === '') {
      setWizardError('Reference Code and Amount column selections are required.');
      return;
    }

    setConfirmLoading(true);
    setWizardError(null);

    const getHeader = (idx: number | ''): string | undefined => {
      if (idx === '') return undefined;
      return previewData.headers.find((h) => h.column_index === idx)?.header;
    };

    const columnMapping: StatementColumnMapping = {
      reference_id: { column_index: Number(refColIdx), header: getHeader(refColIdx) },
      amount: { column_index: Number(amtColIdx), header: getHeader(amtColIdx) },
      transaction_at: dateColIdx !== '' ? { column_index: Number(dateColIdx), header: getHeader(dateColIdx) } : undefined,
      direction: dirColIdx !== '' ? { column_index: Number(dirColIdx), header: getHeader(dirColIdx) } : undefined,
      utr: utrColIdx !== '' ? { column_index: Number(utrColIdx), header: getHeader(utrColIdx) } : undefined,
      counterparty_name: cpColIdx !== '' ? { column_index: Number(cpColIdx), header: getHeader(cpColIdx) } : undefined,
      description: descColIdx !== '' ? { column_index: Number(descColIdx), header: getHeader(descColIdx) } : undefined,
    };

    try {
      const summary = await statementImportApi.confirmStatementImport({
        preview_token: previewData.preview_token,
        sheet_name: selectedSheet || undefined,
        header_row_index: headerRowIndex,
        column_mapping: columnMapping,
      });

      setImportSummary(summary);
      setStep(5);
    } catch (err: any) {
      setWizardError(err.message || 'Statement import could not be completed.');
    } finally {
      setConfirmLoading(false);
    }
  };

  const copyRegistrationLink = async () => {
    if (!batch) return;
    const rawBasePath = config.basePath || '/upi/';
    const basePath = rawBasePath.endsWith('/') ? rawBasePath : `${rawBasePath}/`;
    const fullUrl = `${window.location.origin}${basePath}register/${batch.public_id}`;
    await navigator.clipboard.writeText(fullUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const mapResultStatusToUI = (status: string) => {
    if (status === 'MATCHED') {
      return { isMatched: true, label: 'Matched', badgeClass: 'active-pill', text: 'Matched' };
    }
    return { isMatched: false, label: 'Not Matched', badgeClass: 'inactive-pill', text: status.replace('_', ' ') };
  };

  if (loading) {
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

  if (error || !batch || !summary) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="batches" onNavigate={onNavigate} />
        <div className="card error-card" style={{ marginTop: '2rem' }}>
          <AlertTriangle size={24} color="#ef4444" />
          <h3>Workspace Load Error</h3>
          <p>{error || 'Batch record not found.'}</p>
          <button onClick={() => onNavigate('/upi/admin/batches')} className="btn btn-outline" style={{ marginTop: '1rem' }}>
            <ArrowLeft size={16} /> Back to Batches
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="batches" onNavigate={onNavigate} />

      {/* Cohort Workspace Header Banner */}
      <div className="card workspace-header-card" style={{ marginBottom: '1.5rem', padding: '1.5rem' }}>
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
            <button onClick={copyRegistrationLink} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {copiedLink ? <Check size={16} color="#34d399" /> : <Copy size={16} />}
              <span>{copiedLink ? 'Copied Link!' : 'Copy Registration Link'}</span>
            </button>
            <button onClick={() => { loadBatchHeader(); loadPayments(); }} className="icon-btn" title="Refresh Workspace">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {/* Central Workspace Tab Bar */}
        <div className="workspace-tab-bar" style={{ display: 'flex', gap: '8px', marginTop: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          <button
            className={`nav-tab ${activeTab === 'payments' ? 'active' : ''}`}
            onClick={() => setActiveTab('payments')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'payments' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'payments' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
          >
            <CreditCard size={16} />
            <span>Payments & Overview ({summary.payments_generated})</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'bank-transactions' ? 'active' : ''}`}
            onClick={() => setActiveTab('bank-transactions')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'bank-transactions' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'bank-transactions' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
          >
            <FileSpreadsheet size={16} />
            <span>Bank Transactions</span>
          </button>

          <button
            className={`nav-tab ${activeTab === 'reconciliation' ? 'active' : ''}`}
            onClick={() => setActiveTab('reconciliation')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none', background: activeTab === 'reconciliation' ? 'var(--accent-primary)' : 'transparent', color: activeTab === 'reconciliation' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontWeight: 500 }}
          >
            <GitCompare size={16} />
            <span>Reconciliation</span>
          </button>
        </div>
      </div>

      {/* TAB 1: PAYMENTS & OVERVIEW (DEFAULT INITIAL VIEW) */}
      {activeTab === 'payments' && (
        <div>
          {/* Top Section: Ultra-Compact Batch Overview Summary Strip */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '10px 20px',
              marginBottom: '1.25rem',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Generated</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.payments_generated}</span>
              <span style={{ fontSize: '0.75rem', color: '#818cf8', background: 'rgba(129, 140, 248, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                {formatINR(summary.expected_amount_inr)}
              </span>
            </div>

            <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Submitted</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.payments_submitted}</span>
              <span style={{ fontSize: '0.75rem', color: '#fbbf24', background: 'rgba(251, 191, 36, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
                UTR Payer
              </span>
            </div>

            <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Approved</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{summary.payments_approved}</span>
              <span style={{ fontSize: '0.75rem', color: '#34d399', background: 'rgba(52, 211, 153, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                {formatINR(summary.approved_amount_inr)}
              </span>
            </div>

            <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Statements</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.statement_count}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255, 255, 255, 0.05)', padding: '2px 8px', borderRadius: '12px' }}>
                Files
              </span>
            </div>
          </div>

          {/* Main Section: Batch Payments Table (Generated from Public Link) */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h3 style={{ margin: 0 }}>Public Registrations & Payments</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Payment sessions generated for candidates registering through the public batch link.
                </p>
              </div>

              {/* Table Header Right Controls: Filters + Select Transaction Dropdown & Match Button */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div className="filter-group">
                  <input
                    type="text"
                    placeholder="Search Ref, Name, UTR..."
                    value={paymentSearch}
                    onChange={(e) => setPaymentSearch(e.target.value)}
                    className="form-input"
                    style={{ width: '170px' }}
                  />
                </div>
                <select
                  value={paymentStatusFilter}
                  onChange={(e) => setPaymentStatusFilter(e.target.value)}
                  className="filter-select"
                >
                  <option value="">All Statuses</option>
                  <option value="PENDING">PENDING</option>
                  <option value="SUBMITTED">SUBMITTED</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="EXPIRED">EXPIRED</option>
                </select>
                <button onClick={() => loadPayments()} className="btn btn-outline btn-sm">
                  <Search size={14} /> Filter
                </button>

                <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 2px' }} />

                {/* Select Transaction Dropdown & Match Button */}
                <select
                  value={selectedStatementIdForPaymentsMatch}
                  onChange={(e) => setSelectedStatementIdForPaymentsMatch(e.target.value)}
                  className="filter-select"
                  style={{ width: '210px', background: 'var(--bg-secondary)', fontWeight: 600, borderColor: '#818cf8' }}
                >
                  <option value="">Select Transaction...</option>
                  {imports.map((imp) => (
                    <option key={imp.public_id} value={imp.public_id}>
                      {imp.filename} ({imp.valid_rows} txns)
                    </option>
                  ))}
                </select>

                <button
                  disabled={!selectedStatementIdForPaymentsMatch || matchingInPaymentsTable}
                  onClick={handleMatchInPaymentsTable}
                  className="btn btn-primary btn-sm"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', borderColor: '#10b981', fontWeight: 600 }}
                >
                  {matchingInPaymentsTable ? (
                    <>
                      <Loader2 size={14} className="spinner" />
                      <span>Matching...</span>
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      <span>Match</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {paymentsLoading ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}><Loader2 size={24} className="spinner" /></div>
            ) : payments.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <CreditCard size={36} color="#6b7280" style={{ margin: '0 auto 8px' }} />
                <p style={{ color: 'var(--text-muted)' }}>No payment sessions generated for this batch yet.</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Share the public registration link with participants to begin collecting payments.
                </p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Participant Name</th>
                      <th>Contact Info</th>
                      <th>Reference ID</th>
                      <th>Fee Amount</th>
                      <th>Submitted UTR</th>
                      <th>Status & Reconciliation</th>
                      <th>Registration Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((p) => {
                      const reconRes = reconResultsBySession[p.payment_session_public_id] || reconResultsBySession[p.reference_id];
                      return (
                        <tr key={p.payment_session_public_id}>
                          <td>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{p.participant_name}</div>
                          </td>
                          <td>
                            <div style={{ fontSize: '0.85rem' }}>{p.phone}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.email}</div>
                          </td>
                          <td className="monospace font-semibold" style={{ color: '#38bdf8' }}>{p.reference_id}</td>
                          <td className="monospace">{formatINR(p.amount_inr)}</td>
                          <td className="monospace">{p.utr || '—'}</td>
                          <td>
                            {p.payment_session_status === 'APPROVED' || reconRes?.status === 'MATCHED' ? (
                              <span className="status-pill active-pill" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', borderColor: '#34d399', fontWeight: 600 }}>
                                <Check size={14} /> Matched
                              </span>
                            ) : reconRes ? (
                              <span className="status-pill inactive-pill" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                ⚠ {reconRes.status.replace('_', ' ')}
                              </span>
                            ) : (
                              <span className={`status-pill ${p.payment_session_status === 'SUBMITTED' ? 'inactive-pill' : 'archived-pill'}`}>
                                {p.payment_session_status}
                              </span>
                            )}
                          </td>
                          <td className="text-sm">{new Date(p.created_at).toLocaleDateString()}</td>
                          <td>
                            <button onClick={() => openPaymentDetail(p.payment_session_public_id)} className="btn-action">
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


        </div>
      )}

      {/* TAB 2: BANK TRANSACTIONS */}
      {activeTab === 'bank-transactions' && (
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.5rem' }}>
          {/* Left Panel: Available Statement Files & Import Trigger */}
          <div>
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Upload size={16} color="#818cf8" /> Statement Import
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                Upload Google Pay or Bank UPI statements (CSV or Excel) with auto sheet detection & column matching.
              </p>
              <button onClick={openWizard} className="btn btn-primary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                <Plus size={16} />
                <span>+ Import Statement File</span>
              </button>
            </div>

            {/* Past Import Files */}
            <div className="card">
              <h4 style={{ marginBottom: '1rem' }}>Available Statements ({imports.length})</h4>
              {importsLoading ? (
                <div style={{ textAlign: 'center', padding: '1rem' }}><Loader2 size={20} className="spinner" /></div>
              ) : imports.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No statement files uploaded yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {imports.map((imp) => (
                    <div
                      key={imp.public_id}
                      onClick={() => loadImportTransactions(imp.public_id)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        background: selectedImportId === imp.public_id ? 'rgba(129, 140, 248, 0.15)' : 'transparent',
                        borderColor: selectedImportId === imp.public_id ? '#818cf8' : 'var(--border-color)',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>{imp.filename}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {imp.valid_rows} rows • {imp.file_type.toUpperCase()}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setItemToDelete(imp);
                          setDeleteModalOpen(true);
                        }}
                        className="btn-action btn-action-danger"
                        title="Delete statement file"
                        style={{ padding: '4px' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Transaction Table for Selected Import */}
          <div>
            {selectedImportId ? (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div>
                    <h3>Bank Statement Transactions</h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Viewing credits recorded in selected statement file.
                    </p>
                  </div>
                  <button onClick={() => selectedImportId && loadImportTransactions(selectedImportId)} className="icon-btn">
                    <RefreshCw size={14} className={txnsLoading ? 'spinner' : ''} />
                  </button>
                </div>

                {txnsLoading ? (
                  <div style={{ padding: '3rem', textAlign: 'center' }}><Loader2 size={24} className="spinner" /></div>
                ) : importTxns.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No transactions found in this statement file.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Direction</th>
                          <th>Reference ID</th>
                          <th>Amount</th>
                          <th>Bank UTR</th>
                          <th>Payer Name</th>
                        </tr>
                      </thead>
                      <tbody>
                        {importTxns.map((t) => (
                          <tr key={t.public_id}>
                            <td><span className={`status-pill ${t.direction === 'CREDIT' ? 'active-pill' : 'inactive-pill'}`}>{t.direction}</span></td>
                            <td className="monospace font-semibold" style={{ color: '#38bdf8' }}>{t.reference_id || '—'}</td>
                            <td className="monospace">{t.amount_inr ? formatINR(t.amount_inr) : '—'}</td>
                            <td className="monospace">{t.utr || '—'}</td>
                            <td>{t.counterparty_name || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="card empty-card">
                <FileSpreadsheet size={36} color="#6b7280" />
                <p>Select a statement file on the left or click "+ Import Statement File" to upload a new statement file.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: RECONCILIATION */}
      {activeTab === 'reconciliation' && (
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
      )}

      {/* 5-Step Full Statement Import Wizard Modal */}
      {wizardOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '680px' }}>
            <div className="modal-header">
              <div>
                <h3>Import Statement File</h3>
                <span className="field-hint">Step {step} of 5</span>
              </div>
              <button onClick={closeWizard} className="icon-btn">
                <X size={16} />
              </button>
            </div>

            {/* Progress Steps */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 600, color: '#64748b', padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', marginBottom: '20px', border: '1px solid var(--border-color)' }}>
              <span style={{ color: step >= 1 ? '#818cf8' : undefined }}>1. Select File</span>
              <span>→</span>
              <span style={{ color: step >= 2 ? '#818cf8' : undefined }}>2. Select Sheet</span>
              <span>→</span>
              <span style={{ color: step >= 3 ? '#818cf8' : undefined }}>3. Match Columns</span>
              <span>→</span>
              <span style={{ color: step >= 4 ? '#818cf8' : undefined }}>4. Preview</span>
              <span>→</span>
              <span style={{ color: step >= 5 ? '#818cf8' : undefined }}>5. Finish</span>
            </div>

            {wizardError && (
              <div className="error-banner" style={{ marginBottom: '16px' }}>
                <AlertTriangle size={16} color="#ef4444" />
                <span>{wizardError}</span>
              </div>
            )}

            {/* Step 1: Upload File */}
            {step === 1 && (
              <div>
                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label">Select Statement File (.csv or .xlsx)</label>
                  <input
                    type="file"
                    accept=".csv, .xlsx, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/csv"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="form-input modal-input"
                    style={{ paddingLeft: '14px', cursor: 'pointer' }}
                  />
                  <span className="field-hint">Supported formats: Google Pay CSV, Paytm CSV/Excel, HDFC / ICICI / SBI Bank Statements.</span>
                </div>

                <div className="form-group" style={{ marginBottom: '20px' }}>
                  <label className="form-label">Title Row Number</label>
                  <input
                    type="number"
                    min={1}
                    value={headerRowIndex}
                    onChange={(e) => setHeaderRowIndex(Math.max(1, parseInt(e.target.value) || 1))}
                    className="form-input modal-input"
                    style={{ maxWidth: '140px' }}
                  />
                  <span className="field-hint">Row number where column titles are located (usually Row 1).</span>
                </div>

                <div className="modal-footer">
                  <button onClick={closeWizard} className="btn btn-outline">Cancel</button>
                  <button
                    disabled={!selectedFile || previewLoading}
                    onClick={() => handleFilePreview()}
                    className="btn btn-primary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {previewLoading ? (
                      <>
                        <Loader2 size={16} className="spinner" />
                        <span>Reading File...</span>
                      </>
                    ) : (
                      <>
                        <Upload size={16} />
                        <span>Next: Inspect Columns →</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Excel Sheet Selection */}
            {step === 2 && previewData && (
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
                  Select Sheet from Excel Workbook
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Your Excel file contains multiple tabs/sheets. Click on the sheet that has your transaction entries:
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                  {previewData.available_sheets.map((sheet) => (
                    <button
                      key={sheet}
                      onClick={() => handleSheetChange(sheet)}
                      className={`btn ${selectedSheet === sheet ? 'btn-primary' : 'btn-outline'}`}
                      style={{ textAlign: 'left', justifyContent: 'flex-start', padding: '12px 14px' }}
                    >
                      📄 {sheet}
                    </button>
                  ))}
                </div>

                <div className="modal-footer">
                  <button onClick={() => setStep(1)} className="btn btn-outline">← Back</button>
                  <button
                    onClick={() => setStep(3)}
                    disabled={!selectedSheet}
                    className="btn btn-primary"
                  >
                    Next: Match Columns →
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Match Statement Columns */}
            {step === 3 && previewData && (
              <div style={{ maxHeight: '60vh', overflowY: 'auto', paddingRight: '4px' }}>
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>Match Statement Columns</h4>
                  <span className="field-hint">
                    Select which column in your uploaded file corresponds to each field below:
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  {/* Reference Code (Required) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">
                      Payment Reference Code / Remarks <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <select
                      value={refColIdx}
                      onChange={(e) => setRefColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">-- Select Column from File --</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                    <span className="field-hint">The unique reference code assigned to participant payment requests.</span>
                  </div>

                  {/* Amount (Required) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">
                      Amount (₹ Rupees) <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <select
                      value={amtColIdx}
                      onChange={(e) => setAmtColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">-- Select Column from File --</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Transaction Date (Optional) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">Transaction Date & Time</label>
                    <select
                      value={dateColIdx}
                      onChange={(e) => setDateColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">(Optional - Skip Column)</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Direction (Optional) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">Credit / Debit Type</label>
                    <select
                      value={dirColIdx}
                      onChange={(e) => setDirColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">(Optional - Skip Column)</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* UTR (Optional) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">Bank Reference Number (UTR / RRN)</label>
                    <select
                      value={utrColIdx}
                      onChange={(e) => setUtrColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">(Optional - Skip Column)</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Payer Name (Optional) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">Payer Name</label>
                    <select
                      value={cpColIdx}
                      onChange={(e) => setCpColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">(Optional - Skip Column)</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Description (Optional) */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label">Description / Remarks</label>
                    <select
                      value={descColIdx}
                      onChange={(e) => setDescColIdx(e.target.value === '' ? '' : Number(e.target.value))}
                      className="filter-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">(Optional - Skip Column)</option>
                      {previewData.headers.map((h, i) => (
                        <option key={h.column_index} value={h.column_index}>
                          Column {i + 1}: {h.header || '(Unnamed Column)'}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="modal-footer" style={{ marginTop: '16px' }}>
                  <button onClick={() => setStep(previewData.available_sheets.length > 1 ? 2 : 1)} className="btn btn-outline">← Back</button>
                  <button onClick={handleProceedToPreviewTable} className="btn btn-primary">Preview Mapped Data →</button>
                </div>
              </div>
            )}

            {/* Step 4: Simple Table Preview */}
            {step === 4 && previewData && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <div>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>Preview Mapped Data</h4>
                    <span className="field-hint">Showing sample entries from file (Total entries: {previewData.total_detected_rows})</span>
                  </div>
                </div>

                <div className="table-responsive" style={{ maxHeight: '240px', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Ref Code</th>
                        <th>Amount (₹)</th>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Bank UTR</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.preview_rows.map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600, color: '#a5b4fc', fontFamily: 'monospace' }}>
                            {refColIdx !== '' ? String(row[refColIdx] ?? '-') : '-'}
                          </td>
                          <td className="amount-highlight font-semibold" style={{ fontFamily: 'monospace' }}>
                            {amtColIdx !== '' ? String(row[amtColIdx] ?? '-') : '-'}
                          </td>
                          <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                            {dateColIdx !== '' ? String(row[dateColIdx] ?? '-') : '-'}
                          </td>
                          <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                            {dirColIdx !== '' ? String(row[dirColIdx] ?? '-') : '-'}
                          </td>
                          <td style={{ fontSize: '0.8rem', color: '#38bdf8', fontFamily: 'monospace' }}>
                            {utrColIdx !== '' ? String(row[utrColIdx] ?? '-') : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="modal-footer" style={{ marginTop: '16px' }}>
                  <button onClick={() => setStep(3)} className="btn btn-outline">← Adjust Columns</button>
                  <button
                    disabled={confirmLoading}
                    onClick={handleConfirmImport}
                    className="btn btn-primary"
                    style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', borderColor: '#10b981' }}
                  >
                    {confirmLoading ? (
                      <>
                        <Loader2 size={16} className="spinner" />
                        <span>Saving Transactions...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={16} />
                        <span>Import Transactions Now ✓</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 5: Simple Completion Summary */}
            {step === 5 && importSummary && (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <div className="icon-badge-success" style={{ margin: '0 auto 16px' }}>
                  <CheckCircle2 size={32} color="#10b981" />
                </div>

                <h4 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#34d399', marginBottom: '6px' }}>
                  {importSummary.already_imported ? 'File Already Imported' : 'Statement Import Successful!'}
                </h4>
                <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '24px' }}>{importSummary.message}</p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '12px', marginBottom: '24px' }}>
                  <div className="summary-section" style={{ padding: '12px' }}>
                    <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
                      {importSummary.total_rows}
                    </span>
                    <span className="detail-label">Total Entries</span>
                  </div>

                  <div className="summary-section" style={{ padding: '12px', background: 'rgba(16,185,129,0.1)' }}>
                    <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#34d399' }}>
                      +{importSummary.new_transactions}
                    </span>
                    <span className="detail-label" style={{ color: '#34d399' }}>New Transactions</span>
                  </div>

                  <div className="summary-section" style={{ padding: '12px', background: 'rgba(245,158,11,0.1)' }}>
                    <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24' }}>
                      {importSummary.duplicate_rows}
                    </span>
                    <span className="detail-label" style={{ color: '#fbbf24' }}>Skipped (Dupes)</span>
                  </div>

                  <div className="summary-section" style={{ padding: '12px' }}>
                    <span style={{ display: 'block', fontSize: '1.4rem', fontWeight: 700, color: '#94a3b8' }}>
                      {importSummary.rows_without_reference}
                    </span>
                    <span className="detail-label">Missing Ref Code</span>
                  </div>
                </div>

                <div className="modal-footer" style={{ justifyContent: 'center' }}>
                  <button onClick={closeWizard} className="btn btn-primary">
                    Done & View Transactions
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Statement Delete Confirmation Modal */}
      {deleteModalOpen && itemToDelete && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ color: '#ef4444' }}>Delete Statement Import</h3>
              <button onClick={() => setDeleteModalOpen(false)} className="icon-btn">
                <X size={16} />
              </button>
            </div>
            <div style={{ padding: '1rem 0' }}>
              <p>Are you sure you want to delete statement file <strong>{itemToDelete.filename}</strong>?</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                This will delete all {itemToDelete.valid_rows} bank transactions imported from this file.
              </p>
            </div>
            <div className="modal-footer">
              <button onClick={() => setDeleteModalOpen(false)} className="btn btn-outline">Cancel</button>
              <button onClick={handleExecuteDelete} disabled={deleteLoading} className="btn btn-danger">
                {deleteLoading ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Payment Session Inspection Drawer / Modal */}
      {selectedPayment && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '560px' }}>
            <div className="modal-header">
              <h3>Payment Session Inspection</h3>
              <button onClick={() => setSelectedPayment(null)} className="icon-btn"><X size={18} /></button>
            </div>
            <div style={{ padding: '1rem 0' }}>
              <p><strong>Participant:</strong> {selectedPayment.participant.full_name} ({selectedPayment.participant.phone})</p>
              <p><strong>Reference ID:</strong> <code style={{ color: '#38bdf8' }}>{selectedPayment.payment.reference_id}</code></p>
              <p><strong>Status:</strong> {selectedPayment.payment.status}</p>
              <p><strong>Amount:</strong> {formatINR(selectedPayment.payment.amount_inr)}</p>
              <p><strong>Submitted UTR:</strong> {selectedPayment.current_submission?.utr || '—'}</p>
            </div>
            <div className="modal-footer">
              <button onClick={() => setSelectedPayment(null)} className="btn btn-outline">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Reconciliation Result Detail Modal */}
      {selectedResultDetail && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3>Reconciliation Result Breakdown</h3>
              <button onClick={() => setSelectedResultDetail(null)} className="icon-btn"><X size={18} /></button>
            </div>
            <div style={{ padding: '1rem 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <h5 style={{ color: '#818cf8', marginBottom: '8px' }}>Bank Transaction</h5>
                <p><strong>Statement File:</strong> {selectedResultDetail.statement_filename}</p>
                <p><strong>Bank Reference:</strong> {selectedResultDetail.bank_reference_id || '—'}</p>
                <p><strong>Bank Amount:</strong> {selectedResultDetail.bank_amount_inr ? formatINR(selectedResultDetail.bank_amount_inr) : '—'}</p>
                <p><strong>Bank UTR:</strong> {selectedResultDetail.bank_utr || '—'}</p>
                <p><strong>Payer:</strong> {selectedResultDetail.bank_counterparty_name || '—'}</p>
              </div>
              <div>
                <h5 style={{ color: '#38bdf8', marginBottom: '8px' }}>Expected Application Payment</h5>
                <p><strong>Participant:</strong> {selectedResultDetail.participant_name || '—'}</p>
                <p><strong>Expected Ref:</strong> {selectedResultDetail.expected_reference_id || '—'}</p>
                <p><strong>Expected Amount:</strong> {selectedResultDetail.expected_amount_inr ? formatINR(selectedResultDetail.expected_amount_inr) : '—'}</p>
                <p><strong>Submitted UTR:</strong> {selectedResultDetail.submitted_utr || '—'}</p>
              </div>
            </div>
            <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '6px', marginTop: '1rem' }}>
              <strong>Result Verdict:</strong> {selectedResultDetail.explanation} ({selectedResultDetail.reason_code})
            </div>
            <div className="modal-footer">
              <button onClick={() => setSelectedResultDetail(null)} className="btn btn-outline">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminBatchWorkspacePage;
