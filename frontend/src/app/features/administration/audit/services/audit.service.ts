import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { AuditLog, AuditPage, AuditQuery } from '../models/audit.models';

@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly http = inject(HttpClient);
  list(query: AuditQuery) { let params = new HttpParams(); const values: Record<string, string | number | undefined> = { search: query.search, user: query.user, action: query.action, entity: query.entity, method: query.method, date_from: query.dateFrom, date_to: query.dateTo, page: query.page, ordering: query.ordering }; Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== '') params = params.set(key, value); }); return this.http.get<AuditPage>('/api/audit-logs/', { params }); }
  get(id: number) { return this.http.get<AuditLog>(`/api/audit-logs/${id}/`); }
}
