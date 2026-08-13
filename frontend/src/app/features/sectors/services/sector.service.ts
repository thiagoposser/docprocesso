import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { OrganizationalUnitPage, Sector, SectorPage, SectorPayload, SectorTreeNode } from '../models/sector.models';

@Injectable({ providedIn: 'root' })
export class SectorService {
  private readonly http = inject(HttpClient);

  units(active = 'true') { return this.http.get<OrganizationalUnitPage>('/api/units/', { params: { active, ordering: 'name' } }); }
  list(search = '', active = '') {
    let params = new HttpParams().set('ordering', 'name');
    if (search) params = params.set('search', search);
    if (active) params = params.set('active', active);
    return this.http.get<SectorPage>('/api/sectors/', { params });
  }
  tree(active = '') { return this.http.get<SectorTreeNode[]>('/api/sectors/tree/', { params: active ? { active } : {} }); }
  get(id: number) { return this.http.get<Sector>(`/api/sectors/${id}/`); }
  create(payload: SectorPayload) { return this.http.post<Sector>('/api/sectors/', payload); }
  update(id: number, payload: Partial<SectorPayload>) { return this.http.patch<Sector>(`/api/sectors/${id}/`, payload); }
}
