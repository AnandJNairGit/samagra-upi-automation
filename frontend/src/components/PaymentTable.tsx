import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
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
    setPage(1);
    setAppliedSearch(searchInput.trim());
  };

  const handleFilterChange = (
    setter: React.Dispatch<React.SetStateAction<string>>,
    value: string
  ) => {
    setPage(1);
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
          <span className="status-badge status-badge-pending">
            <Clock size={11} /> Awaiting Payment
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="status-badge status-badge-submitted">
            <CheckCircle2 size={11} /> Submitted
          </span>
        );
      case 'APPROVED':
        return (
          <span className="status-badge status-badge-approved">
            <CheckCircle2 size={11} /> Approved
          </span>
        );
      case 'REJECTED':
        return (
          <span className="status-badge status-badge-rejected">
            <XCircle size={11} /> Rejected
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="status-badge status-badge-expired">
            <Clock size={11} /> Expired
          </span>
        );
      default:
        return <span className="status-badge">{st}</span>;
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
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
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
              className="filter-select"
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
            <div className="filter-select" style={{ opacity: 0.8, cursor: 'not-allowed', display: 'flex', alignItems: 'center' }}>
              <span>Status: {fixedStatus}</span>
            </div>
          )}

          {/* Course Select */}
          <select
            className="filter-select"
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
            className="filter-select"
            value={batchFilter}
            onChange={(e) => handleFilterChange(setBatchFilter, e.target.value)}
          >
            <option value="">All Batches</option>
            {batches
              .filter((b) => !courseFilter || b.course_public_id === courseFilter)
              .map((b) => (
                <option key={b.public_id} value={b.public_id}>
                  {b.name}
                </option>
              ))}
          </select>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button type="submit" className="btn btn-primary btn-sm">
              Search
            </button>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="btn btn-outline btn-sm"
              >
                Reset
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Main Payment Sessions Card */}
      <div className="card" style={{ padding: 0 }}>
        {/* Card Header & Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>Payment Sessions ({total})</h2>
            {loading && <Loader2 size={15} className="spinner" color="var(--accent-light)" />}
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
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        ) : loading && items.length === 0 ? (
          <div style={{ padding: '8px' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton skeleton-table-row" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
            <p style={{ color: 'var(--text-primary)', fontSize: '1rem', fontWeight: 600 }}>No payments found.</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
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
                        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{item.participant_name}</span>
                        <span className="course-desc-preview">{item.phone} • {item.email}</span>
                      </div>
                    </td>
                    <td>
                      <div className="course-name-cell">
                        <span style={{ color: 'var(--text-primary)' }}>{item.course_name}</span>
                        <span className="course-tag">{item.batch_name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="amount-highlight font-semibold">{formatINR(item.amount_inr)}</span>
                    </td>
                    <td>
                      <span className="monospace font-bold" style={{ fontSize: '0.85rem', color: 'var(--info)' }}>{item.reference_id}</span>
                    </td>
                    <td>
                      {item.utr ? (
                        <span className="monospace" style={{ color: 'var(--accent-light)', fontWeight: 600, fontSize: '0.85rem' }}>
                          {item.utr}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
                      )}
                    </td>
                    <td>{renderStatusBadge(item.payment_session_status)}</td>
                    <td>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--border-color)', background: 'var(--bg-surface)' }}>
            <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Showing Page <strong style={{ color: 'var(--text-primary)' }}>{page}</strong> of <strong style={{ color: 'var(--text-primary)' }}>{totalPages}</strong> ({total} total items)
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
