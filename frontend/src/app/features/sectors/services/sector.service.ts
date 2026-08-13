import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { OrganizationalFunction, OrganizationalFunctionPage, OrganizationalFunctionPayload, OrganizationalUnit, OrganizationalUnitPage, OrganizationalUnitPayload, Sector, SectorPage, SectorPayload, SectorTreeNode } from '../models/sector.models';

@Injectable({ providedIn: 'root' })
export class SectorService {
  private readonly http = inject(HttpClient);

  units(active = 'true') { return this.http.get<OrganizationalUnitPage>('/api/units/', { params: { active, ordering: 'name' } }); }
  functions(active = 'true') { return this.http.get<OrganizationalFunctionPage>('/api/organizational-functions/', { params: { active, ordering: 'name' } }); }
  getUnit(id: number) { return this.http.get<OrganizationalUnit>(`/api/units/${id}/`); }
  createUnit(payload: OrganizationalUnitPayload) { return this.http.post<OrganizationalUnit>('/api/units/', payload); }
  updateUnit(id: number, payload: Partial<OrganizationalUnitPayload>) { return this.http.patch<OrganizationalUnit>(`/api/units/${id}/`, payload); }
  getFunction(id: number) { return this.http.get<OrganizationalFunction>(`/api/organizational-functions/${id}/`); }
  createFunction(payload: OrganizationalFunctionPayload) { return this.http.post<OrganizationalFunction>('/api/organizational-functions/', payload); }
  updateFunction(id: number, payload: Partial<OrganizationalFunctionPayload>) { return this.http.patch<OrganizationalFunction>(`/api/organizational-functions/${id}/`, payload); }
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
