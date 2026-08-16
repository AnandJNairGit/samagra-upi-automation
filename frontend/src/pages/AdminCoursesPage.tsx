import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { getCourses, createCourse, updateCourse } from '../services/courseApi';
import { Course, CourseStatus } from '../types/course';
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
} from 'lucide-react';

interface AdminCoursesPageProps {
  onNavigate: (path: string) => void;
}

export const AdminCoursesPage: React.FC<AdminCoursesPageProps> = ({ onNavigate }) => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Modal States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [courseToArchive, setCourseToArchive] = useState<Course | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);

  // Form States
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formStatus, setFormStatus] = useState<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  const [editStatus, setEditStatus] = useState<CourseStatus>('ACTIVE');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchCourseList = async () => {
    setLoading(true);
    setError(null);
    try {
      const filter = statusFilter === 'ALL' ? undefined : statusFilter;
      const data = await getCourses(filter);
      setCourses(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load courses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourseList();
  }, [statusFilter]);

  const openCreateModal = () => {
    setFormName('');
    setFormDescription('');
    setFormStatus('ACTIVE');
    setFormError(null);
    setIsCreateModalOpen(true);
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = formName.trim();
    if (!cleanName) {
      setFormError('Course name is required.');
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      await createCourse({
        name: cleanName,
        description: formDescription.trim() || undefined,
        status: formStatus,
      });
      setIsCreateModalOpen(false);
      await fetchCourseList();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create course.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const openEditModal = (course: Course) => {
    setSelectedCourse(course);
    setFormName(course.name);
    setFormDescription(course.description || '');
    setEditStatus(course.status);
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleUpdateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourse) return;

    const cleanName = formName.trim();
    if (!cleanName) {
      setFormError('Course name is required.');
      return;
    }

    setFormSubmitting(true);
    setFormError(null);
    try {
      await updateCourse(selectedCourse.public_id, {
        name: cleanName,
        description: formDescription.trim() || undefined,
        status: editStatus,
      });
      setIsEditModalOpen(false);
      setSelectedCourse(null);
      await fetchCourseList();
    } catch (err: any) {
      setFormError(err.message || 'Failed to update course.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleQuickStatusChange = async (course: Course, targetStatus: CourseStatus) => {
    if (targetStatus === 'ARCHIVED') {
      setCourseToArchive(course);
      return;
    }

    try {
      await updateCourse(course.public_id, { status: targetStatus });
      await fetchCourseList();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const confirmArchiveCourse = async () => {
    if (!courseToArchive) return;
    setFormSubmitting(true);
    try {
      await updateCourse(courseToArchive.public_id, { status: 'ARCHIVED' });
      setCourseToArchive(null);
      await fetchCourseList();
    } catch (err: any) {
      alert(`Failed to archive course: ${err.message}`);
    } finally {
      setFormSubmitting(false);
    }
  };

  const getStatusBadge = (status: CourseStatus) => {
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
      <AdminNav activeTab="courses" onNavigate={onNavigate} />

      <header className="page-header">
        <div>
          <h1 className="page-title">Course Management</h1>
          <p className="page-subtitle">Configure training programs, cohorts, and curricula.</p>
        </div>
        <div className="page-actions">
          <button
            onClick={() => fetchCourseList()}
            disabled={loading}
            className="icon-btn"
            title="Refresh Courses"
          >
            <RefreshCw size={16} className={loading ? 'spinner' : ''} />
          </button>
          <button onClick={openCreateModal} className="btn btn-primary">
            <Plus size={16} />
            <span>New Course</span>
          </button>
        </div>
      </header>

      {/* Filter Tabs */}
      <div className="filter-bar">
        <span className="filter-label">Filter by Status:</span>
        <div className="filter-pills">
          {['ALL', 'ACTIVE', 'INACTIVE', 'ARCHIVED'].map((st) => (
            <button
              key={st}
              className={`filter-pill ${statusFilter === st ? 'active' : ''}`}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="card loading-card">
          <Loader2 size={28} className="spinner" color="#818cf8" />
          <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)' }}>Loading courses...</p>
        </div>
      ) : error ? (
        <div className="card error-card">
          <AlertTriangle size={20} color="#ef4444" />
          <p>{error}</p>
          <button onClick={fetchCourseList} className="btn btn-sm btn-outline" style={{ marginTop: '0.75rem' }}>
            Try Again
          </button>
        </div>
      ) : courses.length === 0 ? (
        <div className="card empty-card">
          <Layers size={36} color="#6b7280" />
          <h3>No courses found</h3>
          <p>Get started by creating your first training program.</p>
          <button onClick={openCreateModal} className="btn btn-primary" style={{ marginTop: '1rem' }}>
            <Plus size={16} /> Create Course
          </button>
        </div>
      ) : (
        <div className="table-responsive card">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Course Name</th>
                <th>Status</th>
                <th>Batches</th>
                <th>Created</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course) => {
                const isArchived = course.status === 'ARCHIVED';
                return (
                  <tr key={course.public_id}>
                    <td>
                      <div className="course-name-cell">
                        <span className="font-semibold">{course.name}</span>
                        {course.description && (
                          <span className="course-desc-preview">{course.description}</span>
                        )}
                      </div>
                    </td>
                    <td>{getStatusBadge(course.status)}</td>
                    <td>
                      <span className="count-badge" title="Total cohorts under this course">
                        {course.batch_count} {course.batch_count === 1 ? 'batch' : 'batches'}
                      </span>
                    </td>
                    <td className="monospace text-sm" style={{ color: 'var(--text-muted)' }}>
                      {new Date(course.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          onClick={() => onNavigate(`/upi/admin/batches?course=${course.public_id}`)}
                          className="btn-action"
                          title="View Batches for this course"
                        >
                          <Layers size={15} color="#38bdf8" />
                          <span>Batches</span>
                        </button>

                        {!isArchived ? (
                          <>
                            <button
                              onClick={() => openEditModal(course)}
                              className="btn-action"
                              title="Edit Course"
                            >
                              <Edit2 size={15} color="#a5b4fc" />
                              <span>Edit</span>
                            </button>

                            {course.status === 'ACTIVE' ? (
                              <button
                                onClick={() => handleQuickStatusChange(course, 'INACTIVE')}
                                className="btn-action"
                                title="Deactivate Course"
                              >
                                <XCircle size={15} color="#f59e0b" />
                                <span>Deactivate</span>
                              </button>
                            ) : (
                              <button
                                onClick={() => handleQuickStatusChange(course, 'ACTIVE')}
                                className="btn-action"
                                title="Activate Course"
                              >
                                <CheckCircle2 size={15} color="#10b981" />
                                <span>Activate</span>
                              </button>
                            )}

                            <button
                              onClick={() => handleQuickStatusChange(course, 'ARCHIVED')}
                              className="btn-action btn-action-danger"
                              title="Archive Course"
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

      {/* Create Course Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Create New Course</h3>
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

            <form onSubmit={handleCreateCourse}>
              <div className="form-group">
                <label className="form-label">Course Title *</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Applied Machine Learning"
                  required
                  className="form-input modal-input"
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description (Optional)</label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Overview of curriculum and objectives..."
                  rows={3}
                  className="form-input modal-input"
                  style={{ resize: 'vertical' }}
                  disabled={formSubmitting}
                />
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
                  {formSubmitting ? 'Creating...' : 'Create Course'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Course Modal */}
      {isEditModalOpen && selectedCourse && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Edit Course: {selectedCourse.name}</h3>
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

            <form onSubmit={handleUpdateCourse}>
              <div className="form-group">
                <label className="form-label">Course Title *</label>
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
                <label className="form-label">Description</label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  rows={3}
                  className="form-input modal-input"
                  style={{ resize: 'vertical' }}
                  disabled={formSubmitting}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Lifecycle Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as CourseStatus)}
                  className="form-input modal-input"
                  disabled={formSubmitting}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="ARCHIVED">ARCHIVED (Terminal / Read-Only)</option>
                </select>
                {editStatus === 'ARCHIVED' && (
                  <p className="warning-hint">
                    Warning: Once archived, this course cannot be edited or reactivated.
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

      {/* Archive Confirmation Modal */}
      {courseToArchive && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171' }}>
                <AlertTriangle size={20} />
                Archive Course
              </h3>
              <button onClick={() => setCourseToArchive(null)} className="icon-btn">
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '12px 0 20px', color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
              <p>
                Are you sure you want to archive <strong>{courseToArchive.name}</strong>?
              </p>
              <p style={{ marginTop: '10px', color: '#f87171', fontSize: '0.85rem', lineHeight: '1.4' }}>
                ⚠️ <strong>Archiving is permanent and terminal.</strong> Once archived, this course becomes strictly read-only and cannot be reactivated or edited.
              </p>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                onClick={() => setCourseToArchive(null)}
                disabled={formSubmitting}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmArchiveCourse}
                disabled={formSubmitting}
                className="btn btn-danger"
                style={{ background: '#ef4444', borderColor: '#ef4444', color: '#ffffff' }}
              >
                {formSubmitting ? 'Archiving...' : 'Yes, Archive Course'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
