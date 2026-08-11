import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { StatusBadge } from '../../../../shared/components/status-badge/status-badge';
import { FlatSectorNode, SectorTreeNode } from '../../models/sector.models';
import { SectorService } from '../../services/sector.service';

@Component({
  selector: 'app-sector-list',
  imports: [FormsModule, RouterLink, PageHeader, StatusBadge],
  template: `
    <app-page-header title="Setores" description="Gerencie a estrutura organizacional e seus responsáveis."><a class="btn btn-primary" routerLink="/administracao/setores/novo">+ Novo setor</a></app-page-header>
    <section class="card border-0 shadow-sm"><div class="card-body border-bottom"><div class="row g-3"><div class="col-12 col-md-8"><label class="form-label" for="sector-search">Buscar</label><input id="sector-search" class="form-control" type="search" placeholder="Nome, código ou responsável" [(ngModel)]="search" (keyup.enter)="load()"></div><div class="col-12 col-md-4"><label class="form-label" for="sector-status">Status</label><select id="sector-status" class="form-select" [(ngModel)]="status" (change)="load()"><option value="">Todos</option><option value="true">Ativos</option><option value="false">Inativos</option></select></div></div></div>
      @if (error()) { <div class="alert alert-danger m-3" role="alert">{{ error() }}</div> }
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Setor</th><th>Responsável</th><th>Status</th><th class="text-end">Ações</th></tr></thead><tbody>
        @for (sector of sectors(); track sector.id) { <tr><td><div class="sector-name" [style.padding-left.rem]="sector.level * 1.25"><span class="tree-marker" aria-hidden="true">{{ sector.level ? '↳' : '●' }}</span><strong>{{ sector.name }}</strong>@if (sector.code) { <code>{{ sector.code }}</code> }</div></td><td>{{ sector.manager_name || 'Não definido' }}</td><td><app-status-badge [active]="sector.active" /></td><td class="text-end text-nowrap"><a class="btn btn-sm btn-outline-primary me-1" [routerLink]="['/administracao/setores', sector.id, 'editar']">Editar</a><button class="btn btn-sm btn-outline-secondary" type="button" (click)="toggle(sector)">{{ sector.active ? 'Inativar' : 'Ativar' }}</button></td></tr> }
        @empty { @if (!loading()) { <tr><td colspan="4" class="text-center text-body-secondary py-5">Nenhum setor encontrado.</td></tr> } }
      </tbody></table></div><div class="card-footer bg-white"><small class="text-body-secondary">{{ loading() ? 'Carregando…' : sectors().length + ' setor(es) na hierarquia' }}</small></div></section>
  `,
  styles: [`.sector-name{display:flex;align-items:center;gap:.5rem;min-width:14rem}.tree-marker{color:var(--color-primary);font-size:.75rem}.sector-name code{font-size:.72rem}`]
})
export class SectorList {
  private readonly api = inject(SectorService);
  readonly sectors = signal<FlatSectorNode[]>([]); readonly loading = signal(true); readonly error = signal('');
  search = ''; status = '';
  constructor() { this.load(); }
  load() { this.loading.set(true); this.error.set(''); this.api.tree(this.status).subscribe({ next: tree => { const flat = this.flatten(tree).filter(item => !this.search || `${item.name} ${item.code || ''} ${item.manager_name || ''}`.toLocaleLowerCase().includes(this.search.toLocaleLowerCase())); this.sectors.set(flat); this.loading.set(false); }, error: () => { this.error.set('Não foi possível carregar os setores.'); this.loading.set(false); } }); }
  toggle(sector: FlatSectorNode) { if (sector.active && !window.confirm(`Inativar o setor "${sector.name}"?`)) return; this.error.set(''); this.api.update(sector.id, { active: !sector.active }).subscribe({ next: () => this.load(), error: response => this.error.set(response.error?.active?.[0] || 'Não foi possível alterar o setor.') }); }
  private flatten(nodes: SectorTreeNode[], level = 0): FlatSectorNode[] { return nodes.flatMap(node => [{ ...node, level }, ...this.flatten(node.children, level + 1)]); }
}
