import { useState, useCallback, useMemo, useEffect } from 'react';
import { reconciliationApi } from '../../../services/reconciliationApi';
import { ReconciliationRunResponse, ReconciliationResultResponse } from '../../../types/reconciliation';

export const useBatchReconciliation = (
  batchPublicId: string,
  onRefreshBatch?: () => void
) => {
  const [selectedStatementIdForRecon, setSelectedStatementIdForRecon] = useState<string>('');
  const [activeRun, setActiveRun] = useState<ReconciliationRunResponse | null>(null);
  const [reconResults, setReconResults] = useState<ReconciliationResultResponse[]>([]);
  const [reconResultsLoading, setReconResultsLoading] = useState<boolean>(false);
  const [reconFilter, setReconFilter] = useState<'ALL' | 'MATCHED' | 'NOT_MATCHED'>('ALL');
  const [startingRecon, setStartingRecon] = useState<boolean>(false);

  const loadRunResults = useCallback(async (run: ReconciliationRunResponse) => {
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
  }, []);

  const loadReconHistory = useCallback(async () => {
    try {
      const res = await reconciliationApi.getReconciliationRuns(undefined, batchPublicId, 1, 20);
      if (res.items.length > 0) {
        // Only load the latest run automatically if no active run is set yet,
        // or just always load the latest one if we want to refresh.
        // The original code did `if (res.items.length > 0 && !activeRun)`
        // However since dependencies could be tricky, let's keep it close to original.
        loadRunResults(res.items[0]);
      }
    } catch (err: any) {
      console.error(err);
    }
  }, [batchPublicId, loadRunResults]);

  useEffect(() => {
    if (batchPublicId) {
      loadReconHistory();
    }
  }, [batchPublicId, loadReconHistory]);

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
      if (onRefreshBatch) {
        onRefreshBatch();
      }
    } catch (err: any) {
      alert(`Reconciliation execution failed: ${err.message}`);
    } finally {
      setStartingRecon(false);
    }
  };

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

  return {
    selectedStatementIdForRecon,
    setSelectedStatementIdForRecon,
    activeRun,
    reconResults,
    reconResultsLoading,
    reconFilter,
    setReconFilter,
    startingRecon,
    handleExecuteReconciliation,
    loadReconHistory,
    loadRunResults,
    reconResultsBySession
  };
};
