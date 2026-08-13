import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { FlatSectorNode, SectorTreeNode } from '../../../sectors/models/sector.models';
import { SectorService } from '../../../sectors/services/sector.service';
import { PROCESS_STATUS_LABELS, ProcessItem, ProcessStatus, ProcessType } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-list', imports: [DatePipe, FormsModule, RouterLink, PageHeader],
  template: `
    <app-page-header title="Processos" description="Consulte e acompanhe os processos administrativos do seu escopo.">
      @if (auth.can('processes.add_administrativeprocess')) { <a class="btn btn-primary" routerLink="/processos/novo">+ Novo processo</a> }
    </app-page-header>
    <nav class="nav nav-pills gap-2 mb-3" aria-label="Categorias da caixa de trabalho">@for (item of workboxScopes; track item.value) { <button class="nav-link" [class.active]="workboxScope === item.value" type="button" (click)="selectScope(item.value)">{{ item.label }}</button> }</nav>
    <section class="card border-0 shadow-sm">
      <div class="card-body border-bottom"><div class="row g-3">
        <div class="col-12 col-lg-4"><label class="form-label" for="process-search">Buscar</label><input id="process-search" class="form-control" type="search" maxlength="100" placeholder="Número, texto, nota, fornecedor, setor ou responsável" [(ngModel)]="search" (keyup.enter)="applyFilters()"></div>
        <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="process-assignee">Responsável</label><input id="process-assignee" class="form-control" inputmode="numeric" placeholder="ID do usuário" [(ngModel)]="assignee" (keyup.enter)="applyFilters()"></div>
        <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="process-type">Classificação</label><select id="process-type" class="form-select" [(ngModel)]="type" (change)="applyFilters()"><option value="">Todas</option>@for (item of types(); track item.id) { <option [value]="item.id">{{ item.name }}</option> }</select></div>
        <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="process-status">Estado</label><select id="process-status" class="form-select" [(ngModel)]="status" (change)="applyFilters()"><option value="">Todos</option>@for (item of statuses; track item) { <option [value]="item">{{ labels[item] }}</option> }</select></div>
        <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="process-sector">Setor</label><select id="process-sector" class="form-select" [(ngModel)]="sector" (change)="applyFilters()"><option value="">Todos</option>@for (item of sectors(); track item.id) { <option [value]="item.id">{{ '— '.repeat(item.level) }}{{ item.name }}</option> }</select></div>
        <div class="col-12 col-sm-6 col-lg-2"><label class="form-label" for="process-order">Ordenação</label><select id="process-order" class="form-select" [(ngModel)]="ordering" (change)="applyFilters()"><option value="-updated_at">Mais recentes</option><option value="updated_at">Mais antigos</option><option value="title">Título A–Z</option><option value="number">Número</option></select></div>
      </div></div>
      @if (error()) { <div class="alert alert-danger m-3" role="alert">{{ error() }}</div> }
      <div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light"><tr><th>Processo</th><th>Classificação</th><th>Setor atual</th><th>Responsável</th><th>Estado</th><th>Atualização</th><th class="text-end">Ações</th></tr></thead><tbody>
        @for (item of processes(); track item.id) { <tr><td><strong class="d-block">{{ item.number }}</strong><span>{{ item.title }}</span></td><td>{{ item.process_type_name }}</td><td>{{ item.current_sector_name || item.origin_sector_name }}</td><td>{{ item.assignee_name || 'Não definido' }}</td><td><span class="badge" [class]="statusClass(item.status)">{{ labels[item.status] }}</span></td><td class="text-nowrap">{{ item.updated_at | date:'short' }}</td><td class="text-end text-nowrap"><a class="btn btn-sm btn-light me-1" [routerLink]="['/processos', item.id]">Visualizar</a>@if (canEdit(item)) { <a class="btn btn-sm btn-outline-primary" [routerLink]="['/processos', item.id, 'editar']">Editar</a> }</td></tr> }
        @empty { @if (!loading()) { <tr><td colspan="7" class="text-center text-body-secondary py-5">Nenhum processo encontrado.</td></tr> } }
      </tbody></table></div>
      <div class="card-footer bg-white d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2"><small class="text-body-secondary">{{ loading() ? 'Carregando…' : 'Exibindo ' + processes().length + ' de ' + count() + ' processos' }}</small><nav aria-label="Paginação"><ul class="pagination pagination-sm mb-0"><li class="page-item" [class.disabled]="page() === 1"><button class="page-link" type="button" (click)="goTo(page() - 1)">Anterior</button></li><li class="page-item active"><span class="page-link">{{ page() }}</span></li><li class="page-item" [class.disabled]="!next()"><button class="page-link" type="button" (click)="goTo(page() + 1)">Próxima</button></li></ul></nav></div>
    </section>`
})
export class ProcessList {
  readonly auth = inject(AuthService); private readonly api = inject(ProcessService); private readonly sectorApi = inject(SectorService);
  readonly processes = signal<ProcessItem[]>([]); readonly types = signal<ProcessType[]>([]); readonly sectors = signal<FlatSectorNode[]>([]);
  readonly count = signal(0); readonly next = signal<string | null>(null); readonly page = signal(1); readonly loading = signal(true); readonly error = signal('');
  readonly labels = PROCESS_STATUS_LABELS; readonly statuses = Object.keys(PROCESS_STATUS_LABELS) as ProcessStatus[];
  readonly workboxScopes = [{ value: 'my-action', label: 'Aguardando minha ação' }, { value: 'my-sector', label: 'Meu setor' }, { value: 'created', label: 'Criados por mim' }, { value: 'following', label: 'Acompanhando' }, { value: 'completed', label: 'Concluídos' }];
  search = ''; type = ''; status = ''; sector = ''; assignee = ''; ordering = '-updated_at';
  workboxScope = 'my-action';
  constructor() { this.api.types().subscribe({ next: items => this.types.set(items), error: response => this.handleError(response) }); this.sectorApi.tree('true').subscribe({ next: tree => this.sectors.set(this.flatten(tree)), error: response => this.handleError(response) }); this.load(); }
  applyFilters() { this.page.set(1); this.load(); }
  selectScope(scope: string) { if (this.workboxScope === scope) return; this.workboxScope = scope; this.page.set(1); this.load(); }
  goTo(page: number) { if (page < 1 || (page > this.page() && !this.next())) return; this.page.set(page); this.load(); }
  canEdit(item: ProcessItem) { return item.status === 'DRAFT' && this.auth.canInSector('processes.change_administrativeprocess', item.origin_sector); }
  statusClass(value: ProcessStatus) { return `text-bg-${value === 'COMPLETED' ? 'success' : value === 'CANCELLED' ? 'danger' : value === 'DRAFT' ? 'secondary' : 'primary'}`; }
  private load() { this.loading.set(true); this.error.set(''); this.api.workbox(this.workboxScope, { search: this.search, type: this.type, status: this.status, sector: this.sector, assignee: this.assignee, ordering: this.ordering, page: this.page() }).subscribe({ next: result => { this.processes.set(result.results); this.count.set(result.count); this.next.set(result.next); this.loading.set(false); }, error: response => { this.handleError(response); this.loading.set(false); } }); }
  private handleError(response: { status?: number }) { this.error.set(response?.status === 403 ? 'Você não possui permissão para consultar processos.' : response?.status === 404 ? 'Recurso não encontrado.' : response?.status === 409 ? 'Os dados foram alterados por outro usuário. Atualize a consulta.' : 'Não foi possível carregar os processos.'); }
  private flatten(nodes: SectorTreeNode[], level = 0): FlatSectorNode[] { return nodes.flatMap(node => [{ ...node, level }, ...this.flatten(node.children, level + 1)]); }
}
