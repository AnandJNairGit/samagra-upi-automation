import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { getBatches, createBatch, updateBatch } from '../services/batchApi';
import { getCourses } from '../services/courseApi';
import { Batch, BatchStatus } from '../types/batch';
import { Course } from '../types/course';
import {
  Plus,
  Edit2,
  Archive,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Layers,
  X,
  Lock,
  Calendar,
} from 'lucide-react';

interface AdminBatchesPageProps {
  onNavigate: (path: string) => void;
}

export const AdminBatchesPage: React.FC<AdminBatchesPageProps> = ({ onNavigate }) => {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // URL-driven query params
  const getSearchParams = () => new URLSearchParams(window.location.search);
  const [selectedCourseFilter, setSelectedCourseFilter] = useState<string>(
    getSearchParams().get('course') || getSearchParams().get('course_public_id') || 'ALL'
  );
  const [statusFilter, setStatusFilter] = useState<string>(
    getSearchParams().get('status') || 'ALL'
  );

  // Modal States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [batchToArchive, setBatchToArchive] = useState<Batch | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);

  // Form States
  const [formCourseId, setFormCourseId] = useState('');
  const [formName, setFormName] = useState('');
  const [formAmount, setFormAmount] = useState<string>('1000');
  const [formStartsAt, setFormStartsAt] = useState('');
  const [formEndsAt, setFormEndsAt] = useState('');
  const [formStatus, setFormStatus] = useState<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  const [editStatus, setEditStatus] = useState<BatchStatus>('ACTIVE');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Synchronize URL query params
  const updateUrlParams = (newCourse: string, newStatus: string) => {
    const params = new URLSearchParams();
    if (newCourse && newCourse !== 'ALL') {
      params.set('course', newCourse);
    }
    if (newStatus && newStatus !== 'ALL') {
      params.set('status', newStatus);
    }
    const query = params.toString();
    const newPath = query ? `${window.location.pathname}?${query}` : window.location.pathname;
    window.history.replaceState({}, '', newPath);
  };

  const handleCourseFilterChange = (val: string) => {
    setSelectedCourseFilter(val);
    updateUrlParams(val, statusFilter);
  };

  const handleStatusFilterChange = (val: string) => {
    setStatusFilter(val);
    updateUrlParams(selectedCourseFilter, val);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [coursesData, batchesData] = await Promise.all([
        getCourses(),
        getBatches(
          selectedCourseFilter === 'ALL' ? undefined : selectedCourseFilter,
          statusFilter === 'ALL' ? undefined : statusFilter
        ),
      ]);
      setCourses(coursesData);
      setBatches(batchesData);
    } catch (err: any) {
      setError(err.message || 'Failed to load batch data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCourseFilter, statusFilter]);

  const openCreateModal = () => {
    const initialCourse = selectedCourseFilter !== 'ALL' ? selectedCourseFilter : courses[0]?.public_id || '';
    setFormCourseId(initialCourse);
    setFormName('');
    setFormAmount('2000');
    setFormStartsAt('');
    setFormEndsAt('');
    setFormStatus('ACTIVE');
    setFormError(null);
    setIsCreateModalOpen(true);
  };

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = formName.trim();
    if (!cleanName) {
      setFormError('Batch name is required.');
      return;
    }
    if (!formCourseId) {
      setFormError('Please select a course for this batch.');
      return;
    }

    const amountNum = parseInt(formAmount, 10);
    if (isNaN(amountNum) || amountNum <= 0) {
      setFormError('Amount must be a positive whole INR value (e.g. 2000).');
      return;
    }

    if (formStartsAt && formEndsAt && formEndsAt < formStartsAt) {
      setFormError('End date must be on or after start date.');
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      await createBatch({
        course_public_id: formCourseId,
        name: cleanName,
        amount_inr: amountNum,
        status: formStatus,
        starts_at: formStartsAt ? new Date(formStartsAt).toISOString() : undefined,
        ends_at: formEndsAt ? new Date(formEndsAt).toISOString() : undefined,
      });
      setIsCreateModalOpen(false);
      await loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create batch.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const openEditModal = (batch: Batch) => {
    setSelectedBatch(batch);
    setFormCourseId(batch.course_public_id);
    setFormName(batch.name);
    setFormAmount(String(batch.amount_inr));
    setFormStartsAt(batch.starts_at ? batch.starts_at.slice(0, 10) : '');
    setFormEndsAt(batch.ends_at ? batch.ends_at.slice(0, 10) : '');
    setEditStatus(batch.status);
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleUpdateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBatch) return;

    const cleanName = formName.trim();
    if (!cleanName) {
      setFormError('Batch name is required.');
      return;
    }

    const amountNum = parseInt(formAmount, 10);
    if (isNaN(amountNum) || amountNum <= 0) {
      setFormError('Amount must be a positive whole INR value.');
      return;
    }

    if (formStartsAt && formEndsAt && formEndsAt < formStartsAt) {
      setFormError('End date must be on or after start date.');
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      await updateBatch(selectedBatch.public_id, {
        course_public_id: formCourseId !== selectedBatch.course_public_id ? formCourseId : undefined,
        name: cleanName,
        amount_inr: amountNum,
        status: editStatus,
        starts_at: formStartsAt ? new Date(formStartsAt).toISOString() : undefined,
        ends_at: formEndsAt ? new Date(formEndsAt).toISOString() : undefined,
      });
      setIsEditModalOpen(false);
      setSelectedBatch(null);
      await loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to update batch.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleQuickStatusChange = async (batch: Batch, targetStatus: BatchStatus) => {
    if (targetStatus === 'ARCHIVED') {
      setBatchToArchive(batch);
      return;
    }

    try {
      await updateBatch(batch.public_id, { status: targetStatus });
      await loadData();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const confirmArchiveBatch = async () => {
    if (!batchToArchive) return;
    setFormSubmitting(true);
    try {
      await updateBatch(batchToArchive.public_id, { status: 'ARCHIVED' });
      setBatchToArchive(null);
      await loadData();
    } catch (err: any) {
      alert(`Failed to archive batch: ${err.message}`);
    } finally {
      setFormSubmitting(false);
    }
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const getStatusBadge = (status: BatchStatus) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="status-pill active-pill">
            <CheckCircle2 size={12} /> Active
          </span>
        );
      case 'INACTIVE':
        return (
          <span className="status-pill inactive-pill">
            <XCircle size={12} /> Inactive
          </span>
        );
      case 'ARCHIVED':
        return (
          <span className="status-pill archived-pill">
            <Lock size={12} /> Archived
          </span>
        );
    }
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="batches" onNavigate={onNavigate} />

      <header className="page-header">
        <div>
          <h1 className="page-title">Batch & Cohort Management</h1>
          <p className="page-subtitle">Manage training cohort dates, fee amounts, and course assignments.</p>
        </div>
        <div className="page-actions">
          <button onClick={() => loadData()} disabled={loading} className="icon-btn" title="Refresh Batches">
            <RefreshCw size={16} className={loading ? 'spinner' : ''} />
          </button>
          <button onClick={openCreateModal} className="btn btn-primary">
            <Plus size={16} />
            <span>New Batch</span>
          </button>
        </div>
      </header>

      {/* Dual Filter Toolbar */}
      <div className="filter-toolbar card">
        <div className="filter-group">
          <label className="filter-label">Course:</label>
          <select
            value={selectedCourseFilter}
            onChange={(e) => handleCourseFilterChange(e.target.value)}
            className="filter-select"
          >
            <option value="ALL">All Courses</option>
            {courses.map((c) => (
              <option key={c.public_id} value={c.public_id}>
                {c.name} ({c.status})
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">Status:</label>
          <div className="filter-pills">
            {['ALL', 'ACTIVE', 'INACTIVE', 'ARCHIVED'].map((st) => (
              <button
                key={st}
                className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
                onClick={() => handleStatusFilterChange(st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="card loading-card">
          <Loader2 size={28} className="spinner" color="#818cf8" />
          <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)' }}>Loading batches...</p>
        </div>
      ) : error ? (
        <div className="card error-card">
          <AlertTriangle size={20} color="#ef4444" />
          <p>{error}</p>
          <button onClick={loadData} className="btn btn-sm btn-outline" style={{ marginTop: '0.75rem' }}>
            Try Again
          </button>
        </div>
      ) : batches.length === 0 ? (
        <div className="card empty-card">
          <Layers size={36} color="#6b7280" />
          <h3>No batches found</h3>
          <p>Create a cohort to begin configuring payments and schedules.</p>
          <button onClick={openCreateModal} className="btn btn-primary" style={{ marginTop: '1rem' }}>
            <Plus size={16} /> Create Batch
          </button>
        </div>
      ) : (
        <div className="table-responsive card">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Batch Name</th>
                <th>Course</th>
                <th>Fee (INR)</th>
                <th>Schedule</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => {
                const isArchived = batch.status === 'ARCHIVED';
                return (
                  <tr key={batch.public_id}>
                    <td>
                      <span className="font-semibold">{batch.name}</span>
                    </td>
                    <td>
                      <span className="course-tag">
                        {batch.course_name || 'Assigned Course'}
                      </span>
                    </td>
                    <td>
                      <span className="amount-highlight font-semibold monospace">
                        {formatINR(batch.amount_inr)}
                      </span>
                    </td>
                    <td>
                      <div className="date-cell text-sm">
                        {batch.starts_at || batch.ends_at ? (
                          <>
                            <Calendar size={13} color="#94a3b8" />
                            <span>
                              {batch.starts_at ? new Date(batch.starts_at).toLocaleDateString() : '—'}
                              {' to '}
                              {batch.ends_at ? new Date(batch.ends_at).toLocaleDateString() : '—'}
                            </span>
                          </>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>Self-paced / Open</span>
                        )}
                      </div>
                    </td>
                    <td>{getStatusBadge(batch.status)}</td>
                    <td>
                      <div className="table-actions">
                        {!isArchived ? (
                          <>
                            <button
                              onClick={() => openEditModal(batch)}
                              className="btn-action"
                              title="Edit Batch"
                            >
                              <Edit2 size={15} color="#a5b4fc" />
                              <span>Edit</span>
                            </button>

                            {batch.status === 'ACTIVE' ? (
                              <button
                                onClick={() => handleQuickStatusChange(batch, 'INACTIVE')}
                                className="btn-action"
                                title="Deactivate Batch"
                              >
                                <XCircle size={15} color="#f59e0b" />
                                <span>Deactivate</span>
                              </button>
                            ) : (
                              <button
                                onClick={() => handleQuickStatusChange(batch, 'ACTIVE')}
                                className="btn-action"
                                title="Activate Batch"
                              >
                                <CheckCircle2 size={15} color="#10b981" />
                                <span>Activate</span>
                              </button>
                            )}

                            <button
                              onClick={() => handleQuickStatusChange(batch, 'ARCHIVED')}
                              className="btn-action btn-action-danger"
                              title="Archive Batch"
                            >
                              <Archive size={15} color="#ef4444" />
                              <span>Archive</span>
                            </button>
                          </>
                        ) : (
                          <span className="read-only-tag">Read-Only</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Batch Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Create New Batch</h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div className="error-banner">
                <AlertTriangle size={16} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateBatch}>
              <div className="form-group">
                <label className="form-label">Associated Course *</label>
                <select
                  value={formCourseId}
                  onChange={(e) => setFormCourseId(e.target.value)}
                  required
                  className="form-input modal-input"
                  disabled={formSubmitting}
                >
                  <option value="" disabled>Select Course</option>
                  {courses
                    .filter((c) => c.status !== 'ARCHIVED')
                    .map((c) => (
                      <option key={c.public_id} value={c.public_id}>
                        {c.name} ({c.status})
                      </option>
                    ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Batch / Cohort Title *</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. August 2026 Weekend"
                  required
                  className="form-input modal-input"
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Payment Amount (Whole INR ₹) *</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={formAmount}
                  onChange={(e) => setFormAmount(e.target.value)}
                  placeholder="2000"
                  required
                  className="form-input modal-input monospace"
                  disabled={formSubmitting}
                />
                <span className="field-hint">Specified in whole rupees (no paise or decimals).</span>
              </div>

              <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
                <div>
                  <label className="form-label">Start Date (Optional)</label>
                  <input
                    type="date"
                    value={formStartsAt}
                    onChange={(e) => setFormStartsAt(e.target.value)}
                    className="form-input modal-input"
                    disabled={formSubmitting}
                  />
                </div>
                <div>
                  <label className="form-label">End Date (Optional)</label>
                  <input
                    type="date"
                    value={formEndsAt}
                    onChange={(e) => setFormEndsAt(e.target.value)}
                    className="form-input modal-input"
                    disabled={formSubmitting}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Initial Status</label>
                <select
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value as 'ACTIVE' | 'INACTIVE')}
                  className="form-input modal-input"
                  disabled={formSubmitting}
                >
                  <option value="ACTIVE">ACTIVE (Published)</option>
                  <option value="INACTIVE">INACTIVE (Draft / Unpublished)</option>
                </select>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={formSubmitting}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="btn btn-primary"
                >
                  {formSubmitting ? 'Creating...' : 'Create Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Batch Modal */}
      {isEditModalOpen && selectedBatch && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Edit Batch: {selectedBatch.name}</h3>
              <button onClick={() => setIsEditModalOpen(false)} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div className="error-banner">
                <AlertTriangle size={16} />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateBatch}>
              <div className="form-group">
                <label className="form-label">Associated Course</label>
                <select
                  value={formCourseId}
                  onChange={(e) => setFormCourseId(e.target.value)}
                  className="form-input modal-input"
                  disabled={formSubmitting}
                >
                  {courses
                    .filter((c) => c.status !== 'ARCHIVED' || c.public_id === selectedBatch.course_public_id)
                    .map((c) => (
                      <option key={c.public_id} value={c.public_id}>
                        {c.name} {c.status === 'ARCHIVED' ? '(Archived)' : ''}
                      </option>
                    ))}
                </select>
                <span className="field-hint">Note: Reassignment is blocked if payment sessions exist.</span>
              </div>

              <div className="form-group">
                <label className="form-label">Batch Title *</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  required
                  className="form-input modal-input"
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Fee Amount (Whole INR ₹) *</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={formAmount}
                  onChange={(e) => setFormAmount(e.target.value)}
                  required
                  className="form-input modal-input monospace"
                  disabled={formSubmitting}
                />
                <span className="field-hint">Existing historical payment sessions will preserve their original amount.</span>
              </div>

              <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
                <div>
                  <label className="form-label">Start Date</label>
                  <input
                    type="date"
                    value={formStartsAt}
                    onChange={(e) => setFormStartsAt(e.target.value)}
                    className="form-input modal-input"
                    disabled={formSubmitting}
                  />
                </div>
                <div>
                  <label className="form-label">End Date</label>
                  <input
                    type="date"
                    value={formEndsAt}
                    onChange={(e) => setFormEndsAt(e.target.value)}
                    className="form-input modal-input"
                    disabled={formSubmitting}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Lifecycle Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as BatchStatus)}
                  className="form-input modal-input"
                  disabled={formSubmitting}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="ARCHIVED">ARCHIVED (Terminal / Read-Only)</option>
                </select>
                {editStatus === 'ARCHIVED' && (
                  <p className="warning-hint">
                    Warning: Once archived, this cohort cannot be edited or reactivated.
                  </p>
                )}
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  disabled={formSubmitting}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="btn btn-primary"
                >
                  {formSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Batch Archive Confirmation Modal */}
      {batchToArchive && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171' }}>
                <AlertTriangle size={20} />
                Archive Batch
              </h3>
              <button onClick={() => setBatchToArchive(null)} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '12px 0 20px', color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
              <p>
                Are you sure you want to archive <strong>{batchToArchive.name}</strong>?
              </p>
              <p style={{ marginTop: '10px', color: '#f87171', fontSize: '0.85rem', lineHeight: '1.4' }}>
                ⚠️ <strong>Archiving is permanent and terminal.</strong> Once archived, this batch becomes strictly read-only and cannot be reactivated or edited.
              </p>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                onClick={() => setBatchToArchive(null)}
                disabled={formSubmitting}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmArchiveBatch}
                disabled={formSubmitting}
                className="btn btn-danger"
                style={{ background: '#ef4444', borderColor: '#ef4444', color: '#ffffff' }}
              >
                {formSubmitting ? 'Archiving...' : 'Yes, Archive Batch'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
