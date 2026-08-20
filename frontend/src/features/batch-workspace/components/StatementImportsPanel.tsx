import React from 'react';
import {
  Upload,
  Plus,
  Loader2,
  Trash2,
  RefreshCw,
  FileSpreadsheet,
  X,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { StatementImportListItem, BankTransactionItem } from '../../../types/statementImport';

// Helper types from the hook to avoid prop drilling madness
export interface StatementImportsPanelProps {
  imports: StatementImportListItem[];
  importsLoading: boolean;
  selectedImportId: string | null;
  importTxns: BankTransactionItem[];
  txnsLoading: boolean;
  loadImportTransactions: (id: string) => void;

  wizardOpen: boolean;
  step: number;
  setStep: (step: number) => void;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  headerRowIndex: number;
  setHeaderRowIndex: (idx: number) => void;
  previewData: any;
  previewLoading: boolean;
  selectedSheet: string | null;
  refColIdx: number | '';
  setRefColIdx: (v: number | '') => void;
  amtColIdx: number | '';
  setAmtColIdx: (v: number | '') => void;
  dateColIdx: number | '';
  setDateColIdx: (v: number | '') => void;
  dirColIdx: number | '';
  setDirColIdx: (v: number | '') => void;
  utrColIdx: number | '';
  setUtrColIdx: (v: number | '') => void;
  cpColIdx: number | '';
  setCpColIdx: (v: number | '') => void;
  descColIdx: number | '';
  setDescColIdx: (v: number | '') => void;
  confirmLoading: boolean;
  importSummary: any;
  wizardError: string | null;

  openWizard: () => void;
  closeWizard: () => void;
  handleFilePreview: (sheetOverride?: string) => void;
  handleSheetChange: (sheetName: string) => void;
  handleProceedToPreviewTable: () => void;
  handleConfirmImport: () => void;

  deleteModalOpen: boolean;
  setDeleteModalOpen: (open: boolean) => void;
  itemToDelete: StatementImportListItem | null;
  setItemToDelete: (item: StatementImportListItem | null) => void;
  deleteLoading: boolean;
  handleExecuteDelete: () => void;
}

export const StatementImportsPanel: React.FC<StatementImportsPanelProps> = ({
  imports,
  importsLoading,
  selectedImportId,
  importTxns,
  txnsLoading,
  loadImportTransactions,
  wizardOpen,
  step,
  setStep,
  selectedFile,
  setSelectedFile,
  headerRowIndex,
  setHeaderRowIndex,
  previewData,
  previewLoading,
  selectedSheet,
  refColIdx, setRefColIdx,
  amtColIdx, setAmtColIdx,
  dateColIdx, setDateColIdx,
  dirColIdx, setDirColIdx,
  utrColIdx, setUtrColIdx,
  cpColIdx, setCpColIdx,
  descColIdx, setDescColIdx,
  confirmLoading,
  importSummary,
  wizardError,
  openWizard,
  closeWizard,
  handleFilePreview,
  handleSheetChange,
  handleProceedToPreviewTable,
  handleConfirmImport,
  deleteModalOpen,
  setDeleteModalOpen,
  itemToDelete,
  setItemToDelete,
  deleteLoading,
  handleExecuteDelete
}) => {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div>
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
                  {previewData.available_sheets.map((sheet: string) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.headers.map((h: any, i: number) => (
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
                      {previewData.preview_rows.map((row: any, idx: number) => (
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
    </div>
  );
};
