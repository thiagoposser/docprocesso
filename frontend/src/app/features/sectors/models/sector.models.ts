import type { PaginatedResponse } from '../../../core/models/application.models';

export interface Sector {
  id: number; name: string; code: string | null; parent: number | null; parent_name: string | null;
  manager: number | null; manager_name: string | null; active: boolean; created_at: string; updated_at: string;
}

export interface SectorTreeNode {
  id: number; name: string; code: string | null; parent: number | null; manager: number | null;
  manager_name: string | null; active: boolean; children: SectorTreeNode[];
}

export interface FlatSectorNode extends SectorTreeNode { level: number; }
export type SectorPage = PaginatedResponse<Sector>;
export interface SectorPayload { name: string; code: string | null; parent: number | null; manager: number | null; active: boolean; }
