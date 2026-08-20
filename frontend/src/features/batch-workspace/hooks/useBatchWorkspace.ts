import { useState, useCallback, useEffect } from 'react';
import { Batch, BatchSummary } from '../../../types/batch';
import { getBatch, getBatchSummary } from '../../../services/batchApi';
import { config } from '../../../core/config';

export type WorkspaceTab = 'payments' | 'bank-transactions' | 'reconciliation';

export const useBatchWorkspace = (batchPublicId: string, initialTab: string = 'payments') => {
  // We explicitly map 'overview' to 'payments' to preserve the existing route semantic
  const [activeTab, setActiveTab] = useState<WorkspaceTab>(
    initialTab === 'overview' ? 'payments' : (initialTab as WorkspaceTab)
  );

  const [batch, setBatch] = useState<Batch | null>(null);
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const loadBatchHeader = useCallback(async () => {
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
  }, [batchPublicId]);

  useEffect(() => {
    loadBatchHeader();
  }, [loadBatchHeader]);

  const copyRegistrationLink = async () => {
    if (!batch) return;
    const rawBasePath = config.basePath || '/upi/';
    const basePath = rawBasePath.endsWith('/') ? rawBasePath : `${rawBasePath}/`;
    const fullUrl = `${window.location.origin}${basePath}register/${batch.public_id}`;
    await navigator.clipboard.writeText(fullUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return {
    activeTab,
    setActiveTab,
    batch,
    summary,
    loading,
    error,
    copiedLink,
    loadBatchHeader,
    copyRegistrationLink
  };
};
