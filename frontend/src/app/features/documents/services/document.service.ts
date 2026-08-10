import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { DocumentCategory, DocumentItem, DocumentPage, DocumentQuery } from '../models/document.models';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private readonly http = inject(HttpClient);

  list(query: DocumentQuery) {
    let params = new HttpParams();
    const values: Record<string, string | number | undefined> = {
      search: query.search, category: query.category, active: query.active,
      ordering: query.ordering, date_from: query.dateFrom, date_to: query.dateTo, page: query.page
    };
    Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== '') params = params.set(key, value); });
    return this.http.get<DocumentPage>('/api/documents/', { params });
  }

  get(id: number) { return this.http.get<DocumentItem>(`/api/documents/${id}/`); }
  create(payload: FormData) { return this.http.post<DocumentItem>('/api/documents/', payload); }
  update(id: number, payload: FormData | object) { return this.http.patch<DocumentItem>(`/api/documents/${id}/`, payload); }
  categories() { return this.http.get<DocumentPageCategory>('/api/document-categories/'); }
  createCategory(name: string) { return this.http.post<DocumentCategory>('/api/document-categories/', { name, active: true }); }
  download(id: number, attachment = false) { return this.http.get(`/api/documents/${id}/download/`, { params: { attachment }, responseType: 'blob' }); }
}

interface DocumentPageCategory { count: number; next: string | null; previous: string | null; results: DocumentCategory[]; }
