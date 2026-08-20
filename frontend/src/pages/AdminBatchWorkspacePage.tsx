import React from 'react';
import { BatchWorkspace } from '../features/batch-workspace';

interface AdminBatchWorkspacePageProps {
  batchPublicId: string;
  onNavigate: (path: string) => void;
  initialTab?: 'overview' | 'payments' | 'bank-transactions' | 'reconciliation';
}

export const AdminBatchWorkspacePage: React.FC<AdminBatchWorkspacePageProps> = (props) => {
  return (
    <BatchWorkspace
      batchPublicId={props.batchPublicId}
      onNavigate={props.onNavigate}
      initialTab={props.initialTab || 'payments'}
    />
  );
};

