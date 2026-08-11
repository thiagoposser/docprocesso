import type { PaginatedResponse } from '../../../core/models/application.models';

export type ProcessStatus = 'DRAFT' | 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'ARCHIVED';

export interface ProcessType {
  id: number; name: string; code: string; description: string;
}

export interface ProcessItem {
  id: number; number: string; title: string; description?: string;
  process_type: number; process_type_name: string; status: ProcessStatus; version: number;
  origin_sector: number; origin_sector_name: string; current_sector: number | null; current_sector_name: string | null;
  assignee: number | null; assignee_name: string | null; created_by?: number; created_by_name?: string;
  opened_at: string | null; completed_at: string | null; archived_at: string | null;
  created_at?: string; updated_at: string;
}

export interface ProcessPayload {
  title: string; description: string; process_type: number; origin_sector: number; assignee: number | null;
}

export interface ProcessQuery {
  search?: string; number?: string; type?: string; status?: string; sector?: string; assignee?: string;
  createdFrom?: string; createdTo?: string; ordering?: string; page?: number;
}

export type ProcessPage = PaginatedResponse<ProcessItem>;

export const PROCESS_STATUS_LABELS: Record<ProcessStatus, string> = {
  DRAFT: 'Rascunho', OPEN: 'Aberto', IN_PROGRESS: 'Em andamento',
  COMPLETED: 'Concluído', CANCELLED: 'Cancelado', ARCHIVED: 'Arquivado'
};
