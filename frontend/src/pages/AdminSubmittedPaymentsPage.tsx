import React from 'react';
import { AdminNav } from '../components/AdminNav';
import { PaymentTable } from '../components/PaymentTable';

interface AdminSubmittedPaymentsPageProps {
  onNavigate: (path: string) => void;
  searchParams?: Record<string, string>;
}

export const AdminSubmittedPaymentsPage: React.FC<AdminSubmittedPaymentsPageProps> = ({
  onNavigate,
  searchParams,
}) => {
  return (
    <div className="admin-page-container">
      <AdminNav activeTab="submitted" onNavigate={onNavigate} />

      <header className="page-header">
        <div className="page-title-bar">
          <h1 className="page-title">Submitted Payments</h1>
          <p className="page-subtitle">
            Review participant UTR transaction claims awaiting verification against statement records.
          </p>
        </div>
      </header>

      <PaymentTable
        fixedStatus="SUBMITTED"
        onNavigate={onNavigate}
        initialFilters={{
          course_public_id: searchParams?.course_public_id,
          batch_public_id: searchParams?.batch_public_id,
          search: searchParams?.search,
        }}
      />
    </div>
  );
};
