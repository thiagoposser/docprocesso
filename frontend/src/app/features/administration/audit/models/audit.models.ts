import type { PaginatedResponse } from '../../../../core/models/application.models';

export interface AuditLog {
  id: number; user: number | null; user_name: string; action: string; action_display: string;
  entity_type: string; entity_id: string; description: string;
  old_values: Record<string, unknown>; new_values: Record<string, unknown>;
  ip_address: string | null; user_agent: string; request_method: string; request_path: string; created_at: string;
}

export interface AuditQuery { search?: string; user?: string; action?: string; entity?: string; method?: string; dateFrom?: string; dateTo?: string; page?: number; ordering?: string; }
export type AuditPage = PaginatedResponse<AuditLog>;
