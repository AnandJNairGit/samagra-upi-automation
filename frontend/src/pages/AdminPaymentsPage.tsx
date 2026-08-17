import React from 'react';
import { AdminNav } from '../components/AdminNav';
import { PaymentTable } from '../components/PaymentTable';
import { CreditCard } from 'lucide-react';

interface AdminPaymentsPageProps {
  onNavigate: (path: string) => void;
  searchParams?: Record<string, string>;
}

export const AdminPaymentsPage: React.FC<AdminPaymentsPageProps> = ({
  onNavigate,
  searchParams,
}) => {
  return (
    <div className="admin-page-container">
      <AdminNav activeTab="payments" onNavigate={onNavigate} />

      <header className="page-header">
        <div>
          <div className="badge success-badge">
            <CreditCard size={14} />
            Phase 8 — Payment Operations
          </div>
          <h1 className="page-title">Payment Management</h1>
          <p className="page-subtitle">
            Inspect payment sessions, reference IDs, status distributions, and participant transaction claims.
          </p>
        </div>
      </header>

      <PaymentTable
        onNavigate={onNavigate}
        initialFilters={{
          status: searchParams?.status,
          course_public_id: searchParams?.course_public_id,
          batch_public_id: searchParams?.batch_public_id,
          search: searchParams?.search,
        }}
      />
    </div>
  );
};
