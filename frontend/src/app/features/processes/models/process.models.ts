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
  workflow_version: number | null; workflow_name: string | null; workflow_version_number: number | null;
  current_stage: number | null; current_stage_name: string | null;
  responsible_sector: number | null; responsible_sector_name: string | null;
  responsible_function: number | null; responsible_function_name: string | null;
  organizational_unit_name: string | null; last_movement_at: string | null; last_movement_action: string | null; last_movement_action_label: string | null;
  opened_at: string | null; completed_at: string | null; archived_at: string | null;
  created_at?: string; updated_at: string;
}

export interface ProcessPayload {
  title: string; description: string; process_type: number; origin_membership?: number;
}

export interface ProcessQuery {
  search?: string; number?: string; type?: string; status?: string; sector?: string; unit?: string; stage?: string;
  responsibleSector?: string; responsibleFunction?: string; assignee?: string; stalled?: string;
  createdFrom?: string; createdTo?: string; ordering?: string; page?: number;
}

export type ProcessPage = PaginatedResponse<ProcessItem>;

export interface WorkflowAction { action: string; label: string; destination_stage: number; destination_stage_name: string; requires_note: boolean; requires_attachment: boolean; required_document_role: string; integration_action: string; is_return: boolean; }
export interface ExecuteTransitionPayload { action: string; version: number; note?: string; }
export interface EligibleAssignee { id: number; username: string; name: string; }

export interface ProcessMovement {
  kind: 'movement' | 'event'; id: string; action: string | null; action_label: string | null;
  event_type: string | null; event_type_label: string | null; title: string;
  from_sector: number | null; from_sector_name: string | null;
  to_sector: number | null; to_sector_name: string | null;
  workflow_version: number | null; workflow_version_number: number | null;
  transition: number | null; transition_code: string | null;
  from_stage: number | null; from_stage_name: string | null;
  to_stage: number | null; to_stage_name: string | null;
  from_responsibility: string | null; to_responsibility: string | null;
  context_snapshot: Record<string, unknown>;
  actor: number | null; actor_name: string | null; note: string; payload: Record<string, unknown>;
  status_before: ProcessStatus | null; status_before_label: string | null;
  status_after: ProcessStatus | null; status_after_label: string | null; created_at: string;
}

export type ProcessTimelinePage = PaginatedResponse<ProcessMovement>;

export interface ProcessAttachment {
  id: number; file_name: string | null; download_url: string | null;
  source_type: 'file' | 'external_url'; active: boolean;
  created_at: string; deactivated_at: string | null;
  workflow_version: number | null; workflow_version_number: number | null;
  stage: number | null; stage_name: string | null; sector: number | null; sector_name: string | null;
  function: number | null; function_name: string | null; context_snapshot: Record<string, unknown>;
}

export interface ProcessDocument {
  id: number; process: number; title: string; description: string;
  category: number; category_name: string; role: 'GENERAL' | 'PAYMENT_RECEIPT'; active: boolean;
  created_by_name: string; created_at: string; updated_at: string;
  attachments: ProcessAttachment[];
}

export type ProcessDocumentPage = PaginatedResponse<ProcessDocument>;

export const PROCESS_STATUS_LABELS: Record<ProcessStatus, string> = {
  DRAFT: 'Rascunho', OPEN: 'Aberto', IN_PROGRESS: 'Em andamento',
  COMPLETED: 'Concluído', CANCELLED: 'Cancelado', ARCHIVED: 'Arquivado'
};
