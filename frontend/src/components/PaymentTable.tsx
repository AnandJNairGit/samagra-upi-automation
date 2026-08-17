import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  Filter,
  Loader2,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-react';
import { getCourses } from '../services/courseApi';
import { getBatches } from '../services/batchApi';
import { fetchAdminPayments, fetchAdminSubmittedPayments } from '../services/adminPaymentApi';
import { AdminPaymentFilterParams, AdminPaymentListItem } from '../types/adminPayment';
import { Course } from '../types/course';
import { Batch } from '../types/batch';

interface PaymentTableProps {
  fixedStatus?: string; // If set (e.g. 'SUBMITTED'), locks the status filter
  onNavigate: (path: string) => void;
  initialFilters?: AdminPaymentFilterParams;
}

export const PaymentTable: React.FC<PaymentTableProps> = ({
  fixedStatus,
  onNavigate,
  initialFilters,
}) => {
  const [items, setItems] = useState<AdminPaymentListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState<number>(initialFilters?.page || 1);
  const [pageSize] = useState<number>(15);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(0);

  // Filter states
  const [statusFilter, setStatusFilter] = useState<string>(
    fixedStatus || initialFilters?.status || ''
  );
  const [courseFilter, setCourseFilter] = useState<string>(
    initialFilters?.course_public_id || ''
  );
  const [batchFilter, setBatchFilter] = useState<string>(
    initialFilters?.batch_public_id || ''
  );
  const [searchInput, setSearchInput] = useState<string>(initialFilters?.search || '');
  const [appliedSearch, setAppliedSearch] = useState<string>(initialFilters?.search || '');

  // Catalog options for dropdown filters
  const [courses, setCourses] = useState<Course[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);

  useEffect(() => {
    async function loadCatalog() {
      try {
        const [cList, bList] = await Promise.all([
          getCourses().catch(() => []),
          getBatches().catch(() => []),
        ]);
        setCourses(cList);
        setBatches(bList);
      } catch {
        // Dropdowns will gracefully remain empty
      }
    }
    loadCatalog();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const filterParams: AdminPaymentFilterParams = {
        status: fixedStatus || statusFilter || undefined,
        course_public_id: courseFilter || undefined,
        batch_public_id: batchFilter || undefined,
        search: appliedSearch || undefined,
        page,
        page_size: pageSize,
      };

      const data = fixedStatus === 'SUBMITTED' && !statusFilter
        ? await fetchAdminSubmittedPayments(filterParams)
        : await fetchAdminPayments(filterParams);

      setItems(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      setError(err.message || 'Unable to load payment records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, statusFilter, courseFilter, batchFilter, appliedSearch, fixedStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); // Reset to page 1 on new search
    setAppliedSearch(searchInput.trim());
  };

  const handleFilterChange = (
    setter: React.Dispatch<React.SetStateAction<string>>,
    value: string
  ) => {
    setPage(1); // Reset page to 1 on any filter change
    setter(value);
  };

  const clearFilters = () => {
    setPage(1);
    if (!fixedStatus) setStatusFilter('');
    setCourseFilter('');
    setBatchFilter('');
    setSearchInput('');
    setAppliedSearch('');
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const renderStatusBadge = (st: string) => {
    switch (st.toUpperCase()) {
      case 'PENDING':
        return (
          <span className="status-pill active-pill" style={{ fontSize: '0.75rem', padding: '3px 8px' }}>
            <Clock size={12} /> Awaiting Payment
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="status-pill status-pill-submitted" style={{ fontSize: '0.75rem', padding: '3px 8px' }}>
            <CheckCircle2 size={12} /> Submitted
          </span>
        );
      case 'APPROVED':
        return (
          <span className="status-pill" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)', fontSize: '0.75rem', padding: '3px 8px' }}>
            <CheckCircle2 size={12} /> Approved
          </span>
        );
      case 'REJECTED':
        return (
          <span className="status-pill" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', fontSize: '0.75rem', padding: '3px 8px' }}>
            <XCircle size={12} /> Rejected
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="status-pill archived-pill" style={{ fontSize: '0.75rem', padding: '3px 8px' }}>
            <Clock size={12} /> Expired
          </span>
        );
      default:
        return <span className="status-pill">{st}</span>;
    }
  };

  const hasActiveFilters =
    (statusFilter && statusFilter !== fixedStatus) ||
    courseFilter ||
    batchFilter ||
    appliedSearch;

  return (
    <div className="payment-table-container">
      {/* Search & Filter Bar */}
      <div className="card filter-bar-card" style={{ marginBottom: '1.5rem', padding: '16px' }}>
        <form onSubmit={handleSearchSubmit} className="filter-form-grid" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: '12px', alignItems: 'center' }}>
          {/* Search Input */}
          <div className="search-input-wrapper" style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Search participant name, phone, email, Ref ID, or UTR..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>

          {/* Status Select */}
          {!fixedStatus ? (
            <select
              className="form-input filter-select"
              value={statusFilter}
              onChange={(e) => handleFilterChange(setStatusFilter, e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="EXPIRED">EXPIRED</option>
            </select>
          ) : (
            <div className="form-input filter-select disabled-input" style={{ opacity: 0.8, cursor: 'not-allowed', display: 'flex', alignItems: 'center' }}>
              <span>Status: {fixedStatus}</span>
            </div>
          )}

          {/* Course Select */}
          <select
            className="form-input filter-select"
            value={courseFilter}
            onChange={(e) => handleFilterChange(setCourseFilter, e.target.value)}
          >
            <option value="">All Courses</option>
            {courses.map((c) => (
              <option key={c.public_id} value={c.public_id}>
                {c.name}
              </option>
            ))}
          </select>

          {/* Batch Select */}
          <select
            className="form-input filter-select"
            value={batchFilter}
            onChange={(e) => handleFilterChange(setBatchFilter, e.target.value)}
          >
            <option value="">All Batches</option>
            {batches.map((b) => (
              <option key={b.public_id} value={b.public_id}>
                {b.name}
              </option>
            ))}
          </select>

          {/* Filter Actions */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button type="submit" className="btn btn-primary" style={{ padding: '8px 14px' }}>
              <Filter size={14} />
              <span>Search</span>
            </button>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="btn btn-outline"
                style={{ padding: '8px 12px' }}
                title="Clear all active filters"
              >
                <span>Reset</span>
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Main Table Card */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        {/* Card Header & Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Payment Sessions ({total})</h2>
            {loading && <Loader2 size={16} className="spinner" color="#818cf8" />}
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="icon-btn"
            title="Refresh payment table"
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
          </button>
        </div>

        {/* Loading / Error / Empty / Table render */}
        {error ? (
          <div className="error-banner" style={{ margin: '20px' }}>
            <AlertCircle size={16} color="#ef4444" />
            <span>{error}</span>
          </div>
        ) : loading && items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0' }}>
            <Loader2 size={32} className="spinner" color="#818cf8" />
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>
              Loading payment records...
            </p>
          </div>
        ) : items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
            <p style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 600 }}>No payments found.</p>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              {hasActiveFilters ? 'Try adjusting or resetting your active search filters.' : 'No payment sessions exist in the system yet.'}
            </p>
            {hasActiveFilters && (
              <button onClick={clearFilters} className="btn btn-outline" style={{ marginTop: '1rem' }}>
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Course & Batch</th>
                  <th>Amount</th>
                  <th>Reference ID</th>
                  <th>Current UTR</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.payment_session_public_id}>
                    <td>
                      <div className="course-name-cell">
                        <span className="font-semibold" style={{ color: '#f8fafc' }}>{item.participant_name}</span>
                        <span className="course-desc-preview">{item.phone} • {item.email}</span>
                      </div>
                    </td>
                    <td>
                      <div className="course-name-cell">
                        <span style={{ color: '#e2e8f0' }}>{item.course_name}</span>
                        <span className="course-tag">{item.batch_name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="amount-highlight font-semibold">{formatINR(item.amount_inr)}</span>
                    </td>
                    <td>
                      <span className="monospace font-bold" style={{ fontSize: '0.85rem' }}>{item.reference_id}</span>
                    </td>
                    <td>
                      {item.utr ? (
                        <span className="monospace" style={{ color: '#38bdf8', fontWeight: 600, fontSize: '0.85rem' }}>
                          {item.utr}
                        </span>
                      ) : (
                        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>—</span>
                      )}
                    </td>
                    <td>{renderStatusBadge(item.payment_session_status)}</td>
                    <td>
                      <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                        {new Date(item.created_at).toLocaleString('en-IN', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => onNavigate(`/upi/admin/payments/${item.payment_session_public_id}`)}
                        className="btn btn-sm btn-outline"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <Eye size={13} />
                        <span>View Details</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.15)' }}>
            <span style={{ fontSize: '0.8125rem', color: '#94a3b8' }}>
              Showing Page <strong style={{ color: '#e2e8f0' }}>{page}</strong> of <strong style={{ color: '#e2e8f0' }}>{totalPages}</strong> ({total} total items)
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="btn btn-sm btn-outline"
              >
                <ChevronLeft size={14} />
                <span>Previous</span>
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="btn btn-sm btn-outline"
              >
                <span>Next</span>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
