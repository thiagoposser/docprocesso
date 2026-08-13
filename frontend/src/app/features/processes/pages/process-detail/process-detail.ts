import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { ProcessActions } from '../../components/process-actions/process-actions';
import { ProcessAssignment } from '../../components/process-assignment/process-assignment';
import { ProcessDocuments } from '../../components/process-documents/process-documents';
import { ProcessTimeline } from '../../components/process-timeline/process-timeline';
import { PROCESS_STATUS_LABELS, ProcessItem, ProcessMovement, ProcessStatus } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-detail', imports: [DatePipe, RouterLink, PageHeader, ProcessActions, ProcessAssignment, ProcessDocuments, ProcessTimeline],
  template: `
    <app-page-header title="Detalhes do processo" description="Consulte os dados, a tramitação e as ações disponíveis."><a class="btn btn-outline-secondary" routerLink="/processos">Voltar</a>@if (canEdit()) { <a class="btn btn-primary" [routerLink]="['/processos', process()!.id, 'editar']">Editar rascunho</a> }</app-page-header>
    @if (error()) { <div class="alert alert-danger" role="alert">{{ error() }}</div> }
    @if (process(); as item) {
      <section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex flex-column flex-md-row justify-content-between gap-3 mb-4"><div><div class="text-body-secondary small mb-1">{{ item.number }}</div><h2 class="h4 mb-1">{{ item.title }}</h2><span class="badge text-bg-light border">{{ item.process_type_name }}</span></div><span class="badge align-self-start" [class]="statusClass(item.status)">{{ labels[item.status] }}</span></div><p class="text-body-secondary">{{ item.description || 'Sem descrição.' }}</p><dl class="row mb-0"><dt class="col-sm-4">Fluxo</dt><dd class="col-sm-8">{{ item.workflow_name ? item.workflow_name + ' · versão ' + item.workflow_version_number : 'Processo legado sem fluxo associado' }}</dd><dt class="col-sm-4">Etapa atual</dt><dd class="col-sm-8">{{ item.current_stage_name || 'Não informada' }}</dd><dt class="col-sm-4">Responsabilidade da etapa</dt><dd class="col-sm-8">{{ item.responsible_sector_name || 'Não definida' }}{{ item.responsible_function_name ? ' · ' + item.responsible_function_name : '' }}</dd><dt class="col-sm-4">Setor de origem</dt><dd class="col-sm-8">{{ item.origin_sector_name }}</dd><dt class="col-sm-4">Setor atual</dt><dd class="col-sm-8">{{ item.current_sector_name || 'Ainda não aberto' }}</dd><dt class="col-sm-4">Responsável individual</dt><dd class="col-sm-8">{{ item.assignee_name || 'Não definido' }}</dd><dt class="col-sm-4">Criado por</dt><dd class="col-sm-8">{{ item.created_by_name }}</dd><dt class="col-sm-4">Versão do registro</dt><dd class="col-sm-8">{{ item.version }}</dd><dt class="col-sm-4">Criado em</dt><dd class="col-sm-8">{{ item.created_at | date:'medium' }}</dd><dt class="col-sm-4">Atualizado em</dt><dd class="col-sm-8">{{ item.updated_at | date:'medium' }}</dd></dl></div></section>
      <app-process-actions [process]="item" (updated)="actionCompleted($event)" (conflict)="reloadAfterConflict()" />
      @if (item.responsible_sector && auth.canInSector('processes.assign_administrativeprocess', item.responsible_sector)) { <app-process-assignment [process]="item" (updated)="actionCompleted($event)" (conflict)="reloadAfterConflict()" /> }
      <app-process-documents [process]="item" (changed)="loadTimeline(1)" />
      @if (auth.can('payments.view_payment') && auth.can('payments.view_financial_data')) { <div class="d-flex justify-content-end mt-3"><a class="btn btn-outline-primary" routerLink="/pagamentos" [queryParams]="{ process: item.id }">Ver pagamentos do processo</a></div> }
      <app-process-timeline [movements]="movements()" [loading]="timelineLoading()" [count]="timelineCount()" [page]="timelinePage()" [hasNext]="timelineNext()" (pageChange)="loadTimeline($event)" />
    }
  `
})
export class ProcessDetail {
  readonly auth = inject(AuthService); private readonly api = inject(ProcessService); private readonly route = inject(ActivatedRoute); private readonly id = Number(this.route.snapshot.paramMap.get('id'));
  readonly process = signal<ProcessItem | null>(null); readonly error = signal(''); readonly labels = PROCESS_STATUS_LABELS;
  readonly movements = signal<ProcessMovement[]>([]); readonly timelineLoading = signal(true); readonly timelineCount = signal(0); readonly timelinePage = signal(1); readonly timelineNext = signal(false);
  constructor() { this.loadProcess(); this.loadTimeline(); }
  canEdit() { const item = this.process(); return Boolean(item && item.status === 'DRAFT' && this.auth.canInSector('processes.change_administrativeprocess', item.origin_sector)); }
  statusClass(value: ProcessStatus) { return `text-bg-${value === 'COMPLETED' ? 'success' : value === 'CANCELLED' ? 'danger' : value === 'DRAFT' ? 'secondary' : 'primary'}`; }
  actionCompleted(item: ProcessItem) { this.process.set(item); this.loadTimeline(1); }
  reloadAfterConflict() { this.loadProcess(); this.loadTimeline(this.timelinePage()); }
  loadTimeline(page = 1) { this.timelineLoading.set(true); this.api.timeline(this.id, page).subscribe({ next: result => { this.movements.set(result.results); this.timelineCount.set(result.count); this.timelinePage.set(page); this.timelineNext.set(Boolean(result.next)); this.timelineLoading.set(false); }, error: () => { this.error.set('Não foi possível carregar o histórico.'); this.timelineLoading.set(false); } }); }
  private loadProcess() { this.api.get(this.id).subscribe({ next: item => this.process.set(item), error: response => this.error.set(response?.status === 403 ? 'Você não possui permissão para consultar este processo.' : 'Processo não encontrado ou fora do seu escopo.') }); }
}
