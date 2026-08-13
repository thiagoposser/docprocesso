import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { OrganizationalUnit } from '../../models/sector.models';
import { SectorService } from '../../services/sector.service';

@Component({
  selector: 'app-unit-list', imports: [FormsModule, RouterLink, PageHeader, StatusBadge],
  template: `
    <app-page-header title="Unidades" description="Gerencie as unidades da estrutura organizacional."><a class="btn btn-primary" routerLink="/administracao/estrutura/unidades/nova">+ Nova unidade</a></app-page-header>
    <section class="card border-0 shadow-sm"><div class="card-body border-bottom"><div class="row g-3"><div class="col-md-8"><label class="form-label" for="unit-search">Buscar</label><input id="unit-search" class="form-control" type="search" [(ngModel)]="search" (keyup.enter)="load()" placeholder="Nome ou sigla"></div><div class="col-md-4"><label class="form-label" for="unit-status">Status</label><select id="unit-status" class="form-select" [(ngModel)]="status" (change)="load()"><option value="">Todos</option><option value="true">Ativas</option><option value="false">Inativas</option></select></div></div></div>
      @if(error()){<div class="alert alert-danger m-3" role="alert">{{error()}}</div>}
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Unidade</th><th>Superior</th><th>Status</th><th class="text-end">Ações</th></tr></thead><tbody>@for(item of filtered();track item.id){<tr><td><strong>{{item.name}}</strong><code class="ms-2">{{item.acronym}}</code><small class="d-block text-body-secondary">{{item.description||'Sem descrição'}}</small></td><td>{{item.parent_name||'Raiz'}}</td><td><app-status-badge [active]="item.active" /></td><td class="text-end"><a class="btn btn-sm btn-outline-primary me-1" [routerLink]="['/administracao/estrutura/unidades',item.id,'editar']">Editar</a><button class="btn btn-sm btn-outline-secondary" type="button" (click)="toggle(item)">{{item.active?'Inativar':'Ativar'}}</button></td></tr>}@empty{@if(!loading()){<tr><td colspan="4" class="text-center text-body-secondary py-5">Nenhuma unidade encontrada.</td></tr>}}</tbody></table></div></section>
  `
})
export class UnitList {
  private readonly api=inject(SectorService); readonly items=signal<OrganizationalUnit[]>([]); readonly loading=signal(true); readonly error=signal(''); search='';status='';
  readonly filtered=()=>this.items().filter(item=>!this.search||`${item.name} ${item.acronym}`.toLowerCase().includes(this.search.toLowerCase()));
  constructor(){this.load();}
  load(){this.loading.set(true);this.error.set('');this.api.units(this.status).subscribe({next:page=>{this.items.set(page.results);this.loading.set(false);},error:()=>{this.error.set('Não foi possível carregar as unidades.');this.loading.set(false);}});}
  toggle(item:OrganizationalUnit){if(item.active&&!window.confirm(`Inativar a unidade "${item.name}"?`))return;this.api.updateUnit(item.id,{active:!item.active}).subscribe({next:()=>this.load(),error:r=>this.error.set(r.error?.active?.[0]||'Não foi possível alterar a unidade.')});}
}
