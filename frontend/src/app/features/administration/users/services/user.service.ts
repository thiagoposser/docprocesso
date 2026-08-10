import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { PaginatedResponse, UserItem, UserPayload } from '../../../../core/models/application.models';

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
}
