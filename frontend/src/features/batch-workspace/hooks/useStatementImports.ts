import { useState, useCallback, useEffect } from 'react';
import { statementImportApi } from '../../../services/statementImportApi';
import {
  StatementImportListItem,
  BankTransactionItem,
  ImportPreviewResponse,
  ImportSummaryResponse,
  StatementColumnMapping,
} from '../../../types/statementImport';

export const useStatementImports = (batchPublicId: string) => {
  // Master Imports List State
  const [imports, setImports] = useState<StatementImportListItem[]>([]);
  const [importsLoading, setImportsLoading] = useState<boolean>(false);
  const [selectedImportId, setSelectedImportId] = useState<string | null>(null);

  // Selected Import Transactions State
  const [importTxns, setImportTxns] = useState<BankTransactionItem[]>([]);
  const [txnsLoading, setTxnsLoading] = useState<boolean>(false);

  // Import Wizard State
  const [wizardOpen, setWizardOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [headerRowIndex, setHeaderRowIndex] = useState<number>(1);
  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [selectedSheet, setSelectedSheet] = useState<string | null>(null);

  // Column Mapping State
  const [refColIdx, setRefColIdx] = useState<number | ''>('');
  const [amtColIdx, setAmtColIdx] = useState<number | ''>('');
  const [dateColIdx, setDateColIdx] = useState<number | ''>('');
  const [dirColIdx, setDirColIdx] = useState<number | ''>('');
  const [utrColIdx, setUtrColIdx] = useState<number | ''>('');
  const [cpColIdx, setCpColIdx] = useState<number | ''>('');
  const [descColIdx, setDescColIdx] = useState<number | ''>('');

  const [confirmLoading, setConfirmLoading] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummaryResponse | null>(null);
  const [wizardError, setWizardError] = useState<string | null>(null);

  // Deletion State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<StatementImportListItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadImports = useCallback(async () => {
    setImportsLoading(true);
    try {
      const res = await statementImportApi.getStatementImports(1, 50);
      setImports(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setImportsLoading(false);
    }
  }, [batchPublicId]);

  useEffect(() => {
    if (batchPublicId) {
      loadImports();
    }
  }, [batchPublicId, loadImports]);

  const loadImportTransactions = async (importPublicId: string) => {
    setSelectedImportId(importPublicId);
    setTxnsLoading(true);
    try {
      const res = await statementImportApi.getImportTransactions(importPublicId, 1, 100);
      setImportTxns(res.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setTxnsLoading(false);
    }
  };

  const openWizard = () => {
    setWizardOpen(true);
    setStep(1);
    setSelectedFile(null);
    setHeaderRowIndex(1);
    setPreviewData(null);
    setSelectedSheet(null);
    setRefColIdx('');
    setAmtColIdx('');
    setDateColIdx('');
    setDirColIdx('');
    setUtrColIdx('');
    setCpColIdx('');
    setDescColIdx('');
    setImportSummary(null);
    setWizardError(null);
  };

  const closeWizard = () => {
    setWizardOpen(false);
    if (step === 5) {
      // If we finished successfully, refresh imports
      loadImports();
    }
  };

  const autoSuggestMappings = (headers: any[]) => {
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

  const handleExecuteDelete = async () => {
    if (!itemToDelete) return;
    setDeleteLoading(true);
    try {
      await statementImportApi.deleteStatementImport(itemToDelete.public_id);
      if (selectedImportId === itemToDelete.public_id) {
        setSelectedImportId(null);
        setImportTxns([]);
      }
      setDeleteModalOpen(false);
      setItemToDelete(null);
      await loadImports();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeleteLoading(false);
    }
  };

  return {
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
    handleExecuteDelete,
  };
};
