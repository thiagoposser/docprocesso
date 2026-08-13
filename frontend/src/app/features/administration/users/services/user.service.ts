import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { PaginatedResponse, UserItem, UserPayload, UserSectorMembership } from '../../../../core/models/application.models';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);
  list(search = '', status = 'all', ordering = 'first_name') {
    let params = new HttpParams().set('ordering', ordering);
    if (search) params = params.set('search', search);
    if (status !== 'all') params = params.set('is_active', String(status === 'active'));
    return this.http.get<PaginatedResponse<UserItem>>('/api/users/', { params });
  }
  get(id: number) { return this.http.get<UserItem>(`/api/users/${id}/`); }
  create(payload: UserPayload) { return this.http.post<UserItem>('/api/users/', payload); }
  update(id: number, payload: Partial<UserPayload>) { return this.http.patch<UserItem>(`/api/users/${id}/`, payload); }
  memberships(user: number) { return this.http.get<PaginatedResponse<UserSectorMembership>>('/api/user-sector-memberships/', { params: { user, active: 'true' } }); }
  addMembership(payload: {user:number;unit:number;sector:number;function:number;active:boolean;is_primary:boolean;is_manager:boolean}) { return this.http.post<UserSectorMembership>('/api/user-sector-memberships/', payload); }
  updateMembership(id: number, payload: Partial<UserSectorMembership>) { return this.http.patch<UserSectorMembership>(`/api/user-sector-memberships/${id}/`, payload); }
}
