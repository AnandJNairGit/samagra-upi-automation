import { apiFetch } from './apiClient';
import { Course, CourseCreateInput, CourseUpdateInput } from '../types/course';

export async function getCourses(status?: string): Promise<Course[]> {
  const url = status ? `/v1/admin/courses?status=${encodeURIComponent(status)}` : '/v1/admin/courses';
  const response = await apiFetch(url, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch courses.');
  }
  return response.json();
}

export async function getCourse(publicId: string): Promise<Course> {
  const response = await apiFetch(`/v1/admin/courses/${publicId}`, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch course details.');
  }
  return response.json();
}

export async function createCourse(data: CourseCreateInput): Promise<Course> {
  const response = await apiFetch('/v1/admin/courses', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create course.');
  }
  return response.json();
}

export async function updateCourse(publicId: string, data: CourseUpdateInput): Promise<Course> {
  const response = await apiFetch(`/v1/admin/courses/${publicId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update course.');
  }
  return response.json();
}
