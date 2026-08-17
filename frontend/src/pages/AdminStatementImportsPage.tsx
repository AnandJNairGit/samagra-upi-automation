import React, { useEffect, useState } from 'react';
import AdminNav from '../components/AdminNav';
import { statementImportApi } from '../services/statementImportApi';
import {
  HeaderItem,
  ImportPreviewResponse,
  ImportSummaryResponse,
  StatementColumnMapping,
  StatementImportListItem,
} from '../types/statementImport';
import {
  FileSpreadsheet,
  Plus,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileText,
  ChevronLeft,
  ChevronRight,
  X,
  Upload,
  Trash2,
} from 'lucide-react';

interface AdminStatementImportsPageProps {
  onNavigate?: (path: string) => void;
}

export const AdminStatementImportsPage: React.FC<AdminStatementImportsPageProps> = ({ onNavigate }) => {
  const navigateTo = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  // History List state
  const [imports, setImports] = useState<StatementImportListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Wizard Modal state
  const [wizardOpen, setWizardOpen] = useState(false);
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [headerRowIndex, setHeaderRowIndex] = useState(1);

  // Step 2 & 3 preview state
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

  // Delete Confirmation Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<StatementImportListItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const confirmDelete = (item: StatementImportListItem) => {
    setItemToDelete(item);
    setDeleteModalOpen(true);
  };

  const handleExecuteDelete = async () => {
    if (!itemToDelete) return;
    setDeleteLoading(true);
    try {
      await statementImportApi.deleteStatementImport(itemToDelete.public_id);
      setDeleteModalOpen(false);
      setItemToDelete(null);
      fetchHistory(page);
    } catch (err: any) {
      setError(err.message || 'Failed to delete statement import.');
    } finally {
      setDeleteLoading(false);
    }
  };

  const fetchHistory = async (targetPage: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await statementImportApi.getStatementImports(targetPage, 20);
      setImports(res.items);
      setTotalCount(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch statement import history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(page);
  }, [page]);

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
    fetchHistory(1);
  };

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

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="statement-imports" onNavigate={navigateTo} />

      <header className="page-header">
        <div>
          <div className="badge">
            <FileSpreadsheet size={14} />
            Bank & UPI Statement Import
          </div>
          <h1 className="page-title">Statement Imports</h1>
          <p className="page-subtitle">
            Upload Google Pay or Bank UPI statements (CSV or Excel) to record bank transactions in the system.
          </p>
        </div>

        <div className="page-actions">
          <button onClick={openWizard} className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} />
            <span>+ Import Statement File</span>
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} color="#ef4444" />
          <span>{error}</span>
        </div>
      )}

      {/* History Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Import History ({totalCount})</h2>
            {loading && <Loader2 size={16} className="spinner" color="#818cf8" />}
          </div>
          <button onClick={() => fetchHistory(page)} disabled={loading} className="icon-btn" title="Refresh history">
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          </button>
        </div>

        {loading && imports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0' }}>
            <Loader2 size={32} className="spinner" color="#818cf8" />
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Loading import history...</p>
          </div>
        ) : imports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <FileSpreadsheet size={40} color="#64748b" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 600 }}>No statement files imported yet.</p>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Click "+ Import Statement File" above to upload your first Google Pay or Bank statement.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Total Entries</th>
                  <th style={{ textAlign: 'right' }}>New Txns</th>
                  <th style={{ textAlign: 'right' }}>Skipped (Dupes)</th>
                  <th>Uploaded By</th>
                  <th>Date Uploaded</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {imports.map((item) => (
                  <tr key={item.public_id}>
                    <td>
                      <span className="font-semibold" style={{ color: '#f8fafc' }}>{item.filename}</span>
                    </td>
                    <td>
                      <span className="count-badge uppercase" style={{ fontWeight: 600 }}>
                        {item.file_type}
                      </span>
                      {item.selected_sheet_name && (
                        <span className="course-tag" style={{ marginLeft: '6px' }}>
                          [{item.selected_sheet_name}]
                        </span>
                      )}
                    </td>
                    <td>
                      {item.status === 'COMPLETED' ? (
                        <span className="status-pill active-pill">Completed</span>
                      ) : item.status === 'COMPLETED_WITH_ERRORS' ? (
                        <span className="status-pill inactive-pill">Completed with Warnings</span>
                      ) : (
                        <span className="status-pill archived-pill">{item.status}</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{item.total_rows}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }} className="amount-highlight font-semibold">
                      +{item.new_transactions}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: '#94a3b8' }}>
                      {item.duplicate_rows}
                    </td>
                    <td>{item.imported_by_name}</td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          onClick={() => navigateTo(`/upi/admin/statement-imports/${item.public_id}`)}
                          className="btn-action"
                        >
                          <FileText size={12} />
                          <span>View Details</span>
                        </button>
                        <button
                          onClick={() => confirmDelete(item)}
                          className="btn-action btn-action-danger"
                          title="Delete this statement import and all associated transactions"
                        >
                          <Trash2 size={12} />
                          <span>Delete</span>
                        </button>
                      </div>
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
              Page {page} of {totalPages} ({totalCount} total imports)
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

      {/* 5-Step Simple Import Wizard Modal */}
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

            {/* User-friendly Progress Steps */}
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
              <div className="error-banner">
                <AlertCircle size={16} color="#ef4444" />
                <span>{wizardError}</span>
              </div>
            )}

            {/* Step 1: Upload File */}
            {step === 1 && (
              <div>
                <div className="form-group">
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

                <div className="form-group">
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
                  Your Excel file contains multiple tabs/sheets. Click on the tab that has your transaction entries:
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

            {/* Step 3: Friendly Column Matching */}
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

                <div className="modal-footer">
                  <button onClick={() => setStep(previewData.available_sheets.length > 1 ? 2 : 1)} className="btn btn-outline">← Back</button>
                  <button onClick={handleProceedToPreviewTable} className="btn btn-primary">Preview Data →</button>
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

                <div className="modal-footer">
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

                <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
                  <button
                    onClick={() => {
                      closeWizard();
                      navigateTo(`/upi/admin/statement-imports/${importSummary.import_public_id}`);
                    }}
                    className="btn btn-primary"
                  >
                    View Import Details →
                  </button>
                  <button onClick={closeWizard} className="btn btn-outline">
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && itemToDelete && (
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
                <strong>{itemToDelete.filename}</strong>
                <div style={{ fontSize: '0.8rem', color: '#f87171', marginTop: '4px' }}>
                  Total entries: {itemToDelete.total_rows} | New transactions: +{itemToDelete.new_transactions}
                </div>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                This action will permanently delete this statement import record and all {itemToDelete.new_transactions} bank transactions recorded from it.
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

export default AdminStatementImportsPage;
