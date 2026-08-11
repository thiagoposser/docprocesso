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

export type ProcessAction = 'open' | 'forward' | 'receive' | 'return' | 'complete' | 'reopen' | 'cancel' | 'archive';

export interface ProcessActionPayload { version: number; destination?: number; note?: string; }

export interface ProcessMovement {
  id: number; action: string; action_label: string;
  from_sector: number | null; from_sector_name: string | null;
  to_sector: number | null; to_sector_name: string | null;
  actor: number; actor_name: string; note: string;
  status_before: ProcessStatus; status_before_label: string;
  status_after: ProcessStatus; status_after_label: string; created_at: string;
}

export type ProcessTimelinePage = PaginatedResponse<ProcessMovement>;

export const PROCESS_STATUS_LABELS: Record<ProcessStatus, string> = {
  DRAFT: 'Rascunho', OPEN: 'Aberto', IN_PROGRESS: 'Em andamento',
  COMPLETED: 'Concluído', CANCELLED: 'Cancelado', ARCHIVED: 'Arquivado'
};
