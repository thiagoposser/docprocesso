import type { PaginatedResponse } from '../../../core/models/application.models';

export interface OrganizationalUnit {
  id: number; name: string; acronym: string; description: string; parent: number | null;
  parent_name: string | null; active: boolean; created_at: string; updated_at: string;
}

export type OrganizationalUnitPage = PaginatedResponse<OrganizationalUnit>;

export interface OrganizationalFunction {
  id: number; name: string; code: string; description: string; active: boolean; created_at: string; updated_at: string;
}

export type OrganizationalFunctionPage = PaginatedResponse<OrganizationalFunction>;

export interface Sector {
  id: number; unit: number | null; unit_name: string | null; unit_acronym: string | null;
  name: string; code: string | null; parent: number | null; parent_name: string | null;
  manager: number | null; manager_name: string | null; active: boolean; created_at: string; updated_at: string;
}

export interface SectorTreeNode {
  id: number; unit: number | null; unit_name: string | null; unit_acronym: string | null;
  name: string; code: string | null; parent: number | null; manager: number | null;
  manager_name: string | null; active: boolean; children: SectorTreeNode[];
}

export interface FlatSectorNode extends SectorTreeNode { level: number; }
export type SectorPage = PaginatedResponse<Sector>;
export interface SectorPayload { unit: number | null; name: string; code: string | null; parent: number | null; manager: number | null; active: boolean; }
