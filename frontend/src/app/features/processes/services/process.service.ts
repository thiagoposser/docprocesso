import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { ProcessAction, ProcessActionPayload, ProcessItem, ProcessPage, ProcessPayload, ProcessQuery, ProcessTimelinePage, ProcessType } from '../models/process.models';

@Injectable({ providedIn: 'root' })
export class ProcessService {
  private readonly http = inject(HttpClient);

  list(query: ProcessQuery = {}) {
    let params = new HttpParams().set('ordering', query.ordering || '-updated_at');
    const values: Record<string, string | number | undefined> = {
      search: query.search, number: query.number, type: query.type, status: query.status,
      sector: query.sector, assignee: query.assignee, created_from: query.createdFrom,
      created_to: query.createdTo, page: query.page
    };
    for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== '') params = params.set(key, value);
    return this.http.get<ProcessPage>('/api/processes/', { params });
  }

  types() { return this.http.get<ProcessType[]>('/api/process-types/'); }
  get(id: number) { return this.http.get<ProcessItem>(`/api/processes/${id}/`); }
  create(payload: ProcessPayload) { return this.http.post<ProcessItem>('/api/processes/', payload); }
  update(id: number, payload: Partial<ProcessPayload>) { return this.http.patch<ProcessItem>(`/api/processes/${id}/`, payload); }
  action(id: number, action: ProcessAction, payload: ProcessActionPayload) { return this.http.post<ProcessItem>(`/api/processes/${id}/${action}/`, payload); }
  timeline(id: number, page = 1) { return this.http.get<ProcessTimelinePage>(`/api/processes/${id}/timeline/`, { params: { page } }); }
}
