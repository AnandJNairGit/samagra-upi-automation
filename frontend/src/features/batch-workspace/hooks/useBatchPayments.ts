import { useState, useCallback, useEffect } from 'react';
import { AdminPaymentListItem } from '../../../types/adminPayment';
import { fetchAdminPayments } from '../../../services/adminPaymentApi';
import { reconciliationApi } from '../../../services/reconciliationApi';
import { ReconciliationRunResponse } from '../../../types/reconciliation';

export const useBatchPayments = (
  batchPublicId: string,
  onMatchSuccess: (run: ReconciliationRunResponse) => Promise<void>
) => {
  const [payments, setPayments] = useState<AdminPaymentListItem[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(false);
  const [paymentSearch, setPaymentSearch] = useState('');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('');
  const [selectedStatementIdForPaymentsMatch, setSelectedStatementIdForPaymentsMatch] = useState<string>('');
  const [matchingInPaymentsTable, setMatchingInPaymentsTable] = useState<boolean>(false);

  const loadPayments = useCallback(async () => {
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
  }, [batchPublicId, paymentStatusFilter, paymentSearch]);

  useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  const handleMatchInPaymentsTable = async () => {
    if (!selectedStatementIdForPaymentsMatch) {
      alert('Please select a bank statement transaction file from the dropdown first.');
      return;
    }
    setMatchingInPaymentsTable(true);
    try {
      const run = await reconciliationApi.startReconciliationRun(batchPublicId, selectedStatementIdForPaymentsMatch);
      await onMatchSuccess(run);
      await loadPayments();
    } catch (err: any) {
      alert(`Matching failed: ${err.message}`);
    } finally {
      setMatchingInPaymentsTable(false);
    }
  };

  return {
    payments,
    paymentsLoading,
    paymentSearch,
    setPaymentSearch,
    paymentStatusFilter,
    setPaymentStatusFilter,
    selectedStatementIdForPaymentsMatch,
    setSelectedStatementIdForPaymentsMatch,
    matchingInPaymentsTable,
    loadPayments,
    handleMatchInPaymentsTable
  };
};
