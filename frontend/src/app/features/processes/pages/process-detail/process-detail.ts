import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { FlatSectorNode, SectorTreeNode } from '../../../sectors/models/sector.models';
import { SectorService } from '../../../sectors/services/sector.service';
import { ProcessActions } from '../../components/process-actions/process-actions';
import { ProcessDocuments } from '../../components/process-documents/process-documents';
import { ProcessTimeline } from '../../components/process-timeline/process-timeline';
import { PROCESS_STATUS_LABELS, ProcessItem, ProcessMovement, ProcessStatus } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-detail', imports: [DatePipe, RouterLink, PageHeader, ProcessActions, ProcessDocuments, ProcessTimeline],
  template: `
    <app-page-header title="Detalhes do processo" description="Consulte os dados, a tramitação e as ações disponíveis."><a class="btn btn-outline-secondary" routerLink="/processos">Voltar</a>@if (canEdit()) { <a class="btn btn-primary" [routerLink]="['/processos', process()!.id, 'editar']">Editar rascunho</a> }</app-page-header>
    @if (error()) { <div class="alert alert-danger" role="alert">{{ error() }}</div> }
    @if (process(); as item) {
      <section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex flex-column flex-md-row justify-content-between gap-3 mb-4"><div><div class="text-body-secondary small mb-1">{{ item.number }}</div><h2 class="h4 mb-1">{{ item.title }}</h2><span class="badge text-bg-light border">{{ item.process_type_name }}</span></div><span class="badge align-self-start" [class]="statusClass(item.status)">{{ labels[item.status] }}</span></div><p class="text-body-secondary">{{ item.description || 'Sem descrição.' }}</p><dl class="row mb-0"><dt class="col-sm-4">Setor de origem</dt><dd class="col-sm-8">{{ item.origin_sector_name }}</dd><dt class="col-sm-4">Setor atual</dt><dd class="col-sm-8">{{ item.current_sector_name || 'Ainda não aberto' }}</dd><dt class="col-sm-4">Responsável</dt><dd class="col-sm-8">{{ item.assignee_name || 'Não definido' }}</dd><dt class="col-sm-4">Criado por</dt><dd class="col-sm-8">{{ item.created_by_name }}</dd><dt class="col-sm-4">Versão</dt><dd class="col-sm-8">{{ item.version }}</dd><dt class="col-sm-4">Criado em</dt><dd class="col-sm-8">{{ item.created_at | date:'medium' }}</dd><dt class="col-sm-4">Atualizado em</dt><dd class="col-sm-8">{{ item.updated_at | date:'medium' }}</dd></dl></div></section>
      <app-process-actions [process]="item" [sectors]="sectors()" [lastAction]="lastAction()" (updated)="actionCompleted($event)" (conflict)="reloadAfterConflict()" />
      <app-process-documents [process]="item" (changed)="loadTimeline(1)" />
      <app-process-timeline [movements]="movements()" [loading]="timelineLoading()" [count]="timelineCount()" [page]="timelinePage()" [hasNext]="timelineNext()" (pageChange)="loadTimeline($event)" />
    }
  `
})
export class ProcessDetail {
  readonly auth = inject(AuthService); private readonly api = inject(ProcessService); private readonly sectorApi = inject(SectorService); private readonly route = inject(ActivatedRoute); private readonly id = Number(this.route.snapshot.paramMap.get('id'));
  readonly process = signal<ProcessItem | null>(null); readonly error = signal(''); readonly labels = PROCESS_STATUS_LABELS; readonly sectors = signal<FlatSectorNode[]>([]);
  readonly movements = signal<ProcessMovement[]>([]); readonly timelineLoading = signal(true); readonly timelineCount = signal(0); readonly timelinePage = signal(1); readonly timelineNext = signal(false);
  readonly lastAction = computed(() => this.timelineNext() ? null : [...this.movements()].reverse().find(item => item.kind === 'movement')?.action || null);
  constructor() { this.loadProcess(); this.loadTimeline(); this.sectorApi.tree('true').subscribe({ next: tree => this.sectors.set(this.flatten(tree)), error: () => this.error.set('Não foi possível carregar os setores disponíveis.') }); }
  canEdit() { const item = this.process(); return Boolean(item && item.status === 'DRAFT' && this.auth.canInSector('processes.change_administrativeprocess', item.origin_sector)); }
  statusClass(value: ProcessStatus) { return `text-bg-${value === 'COMPLETED' ? 'success' : value === 'CANCELLED' ? 'danger' : value === 'DRAFT' ? 'secondary' : 'primary'}`; }
  actionCompleted(item: ProcessItem) { this.process.set(item); this.loadTimeline(1); }
  reloadAfterConflict() { this.loadProcess(); this.loadTimeline(this.timelinePage()); }
  loadTimeline(page = 1) { this.timelineLoading.set(true); this.api.timeline(this.id, page).subscribe({ next: result => { this.movements.set(result.results); this.timelineCount.set(result.count); this.timelinePage.set(page); this.timelineNext.set(Boolean(result.next)); this.timelineLoading.set(false); }, error: () => { this.error.set('Não foi possível carregar o histórico.'); this.timelineLoading.set(false); } }); }
  private loadProcess() { this.api.get(this.id).subscribe({ next: item => this.process.set(item), error: response => this.error.set(response?.status === 403 ? 'Você não possui permissão para consultar este processo.' : 'Processo não encontrado ou fora do seu escopo.') }); }
  private flatten(nodes: SectorTreeNode[], level = 0): FlatSectorNode[] { return nodes.flatMap(node => [{ ...node, level }, ...this.flatten(node.children, level + 1)]); }
}
