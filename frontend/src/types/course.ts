export type CourseStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface Course {
  public_id: string;
  name: string;
  description: string | null;
  status: CourseStatus;
  batch_count: number;
  created_at: string;
  updated_at: string;
}

export interface CourseCreateInput {
  name: string;
  description?: string | null;
  status?: 'ACTIVE' | 'INACTIVE';
}

export interface CourseUpdateInput {
  name?: string;
  description?: string | null;
  status?: CourseStatus;
}
