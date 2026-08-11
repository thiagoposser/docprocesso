import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { PROCESS_STATUS_LABELS, ProcessItem, ProcessStatus } from '../../models/process.models';
import { ProcessService } from '../../services/process.service';

@Component({
  selector: 'app-process-detail', imports: [DatePipe, RouterLink, PageHeader],
  template: `
    <app-page-header title="Detalhes do processo" description="Consulte os dados básicos e a situação atual."><a class="btn btn-outline-secondary" routerLink="/processos">Voltar</a>@if (canEdit()) { <a class="btn btn-primary" [routerLink]="['/processos', process()!.id, 'editar']">Editar rascunho</a> }</app-page-header>
    @if (error()) { <div class="alert alert-danger" role="alert">{{ error() }}</div> }
    @if (process(); as item) { <section class="card border-0 shadow-sm"><div class="card-body p-4"><div class="d-flex flex-column flex-md-row justify-content-between gap-3 mb-4"><div><div class="text-body-secondary small mb-1">{{ item.number }}</div><h2 class="h4 mb-1">{{ item.title }}</h2><span class="badge text-bg-light border">{{ item.process_type_name }}</span></div><span class="badge align-self-start" [class]="statusClass(item.status)">{{ labels[item.status] }}</span></div><p class="text-body-secondary">{{ item.description || 'Sem descrição.' }}</p><dl class="row mb-0"><dt class="col-sm-4">Setor de origem</dt><dd class="col-sm-8">{{ item.origin_sector_name }}</dd><dt class="col-sm-4">Setor atual</dt><dd class="col-sm-8">{{ item.current_sector_name || 'Ainda não aberto' }}</dd><dt class="col-sm-4">Responsável</dt><dd class="col-sm-8">{{ item.assignee_name || 'Não definido' }}</dd><dt class="col-sm-4">Criado por</dt><dd class="col-sm-8">{{ item.created_by_name }}</dd><dt class="col-sm-4">Versão</dt><dd class="col-sm-8">{{ item.version }}</dd><dt class="col-sm-4">Criado em</dt><dd class="col-sm-8">{{ item.created_at | date:'medium' }}</dd><dt class="col-sm-4">Atualizado em</dt><dd class="col-sm-8">{{ item.updated_at | date:'medium' }}</dd></dl></div></section> }
  `
})
export class ProcessDetail {
  readonly auth = inject(AuthService); private readonly api = inject(ProcessService); private readonly route = inject(ActivatedRoute);
  readonly process = signal<ProcessItem | null>(null); readonly error = signal(''); readonly labels = PROCESS_STATUS_LABELS;
  constructor() { this.api.get(Number(this.route.snapshot.paramMap.get('id'))).subscribe({ next: item => this.process.set(item), error: response => this.error.set(response?.status === 403 ? 'Você não possui permissão para consultar este processo.' : 'Processo não encontrado ou fora do seu escopo.') }); }
  canEdit() { const item = this.process(); return Boolean(item && item.status === 'DRAFT' && this.auth.canInSector('processes.change_administrativeprocess', item.origin_sector)); }
  statusClass(value: ProcessStatus) { return `text-bg-${value === 'COMPLETED' ? 'success' : value === 'CANCELLED' ? 'danger' : value === 'DRAFT' ? 'secondary' : 'primary'}`; }
}
