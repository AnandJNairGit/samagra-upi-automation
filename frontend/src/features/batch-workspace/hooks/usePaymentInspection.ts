import { useState } from 'react';
import { reconciliationApi } from '../../../services/reconciliationApi';
import { fetchAdminPaymentDetail } from '../../../services/adminPaymentApi';
import { ReconciliationResultDetailResponse } from '../../../types/reconciliation';
import { AdminPaymentDetailResponse } from '../../../types/adminPayment';

export const usePaymentInspection = () => {
  const [isReconModalOpen, setIsReconModalOpen] = useState(false);
  const [selectedReconResult, setSelectedReconResult] = useState<ReconciliationResultDetailResponse | null>(null);
  const [reconLoading, setReconLoading] = useState(false);
  const [reconError, setReconError] = useState<string | null>(null);

  const [isPaymentDrawerOpen, setIsPaymentDrawerOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<AdminPaymentDetailResponse | null>(null);
  const [paymentLoading, setPaymentLoading] = useState(false);

  const openReconciliationDetail = async (resultPublicId: string) => {
    setIsReconModalOpen(true);
    setReconLoading(true);
    setReconError(null);
    try {
      const detail = await reconciliationApi.getReconciliationResultDetail(resultPublicId);
      setSelectedReconResult(detail);
    } catch (err: any) {
      setReconError(err.message || 'Unable to load reconciliation details. Please try again.');
    } finally {
      setReconLoading(false);
    }
  };

  const openReconciliationDetailBySession = async (sessionPublicId: string) => {
    setIsReconModalOpen(true);
    setReconLoading(true);
    setReconError(null);
    try {
      const detail = await reconciliationApi.getReconciliationResultBySession(sessionPublicId);
      setSelectedReconResult(detail);
    } catch (err: any) {
      setReconError(err.message || 'Unable to load reconciliation details for session. Please try again.');
    } finally {
      setReconLoading(false);
    }
  };

  const openPaymentDetail = async (publicId: string) => {
    // Note: If you have a separate Payment drawer/modal, manage it here.
    setIsPaymentDrawerOpen(true);
    setPaymentLoading(true);
    try {
      const detail = await fetchAdminPaymentDetail(publicId);
      setSelectedPayment(detail);
    } catch (err: any) {
      alert(err.message || 'Failed to load payment details.');
    } finally {
      setPaymentLoading(false);
    }
  };

  const closeInspection = () => {
    setIsReconModalOpen(false);
    setSelectedReconResult(null);
    setReconError(null);

    setIsPaymentDrawerOpen(false);
    setSelectedPayment(null);
  };

  return {
    isReconModalOpen,
    selectedReconResult,
    reconLoading,
    reconError,
    
    isPaymentDrawerOpen,
    selectedPayment,
    paymentLoading,

    openReconciliationDetail,
    openReconciliationDetailBySession,
    openPaymentDetail,
    closeInspection,
  };
};
