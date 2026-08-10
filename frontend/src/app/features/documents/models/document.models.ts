import type { PaginatedResponse } from '../../../core/models/application.models';

export interface DocumentCategory {
  id: number; name: string; slug: string; active: boolean; created_at: string; updated_at: string;
}

export interface DocumentItem {
  id: number; title: string; description: string; category: number; category_name: string;
  file_url: string | null; file_name: string | null; file_size: number | null;
  external_url: string; source_type: 'file' | 'external_url'; active: boolean;
  created_by: number; created_by_name: string; created_at: string; updated_at: string;
}

export interface DocumentQuery {
  search?: string; category?: string; active?: string; ordering?: string;
  dateFrom?: string; dateTo?: string; page?: number;
}

export type DocumentPage = PaginatedResponse<DocumentItem>;
