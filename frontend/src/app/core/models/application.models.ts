export interface DocumentItem {
  id: number; name: string; description: string; category: string; updatedAt: string;
}

export interface UserItem extends AuthUser {}

export interface UserPayload {
  first_name: string; last_name: string; email: string; username: string;
  is_active: boolean; group_names: string[]; password?: string;
}

export interface AuthUser {
  id: number; name: string; first_name: string; last_name: string; username: string;
  email: string; is_active: boolean; is_staff: boolean; groups: string[];
  permissions: string[]; photo_url: string | null; sector_memberships: UserSectorMembershipSummary[]; last_login: string | null; date_joined: string;
}

export interface UserSectorMembershipSummary { id: number; sector: number; sector_name: string; sector_code: string | null; is_primary: boolean; is_manager: boolean; }

export interface TokenPair { access: string; refresh: string; }
export interface LoginResponse extends TokenPair { user: AuthUser; }
export interface RefreshResponse { access: string; refresh?: string; }
export interface PaginatedResponse<T> { count: number; next: string | null; previous: string | null; results: T[]; }
export interface DashboardActivity { id: number; action: string; description: string; user: string; created_at: string; }
export interface DashboardSummary { total_users: number; total_documents: number; api_status: string; environment: string; version: string; recent_activity?: DashboardActivity[]; }
